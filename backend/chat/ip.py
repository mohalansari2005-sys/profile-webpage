import ipaddress


def client_ip(request) -> str:
    """The one place the client address is derived. Never stored raw.

    Lives in its own module so views and throttling can both import it
    without importing each other.

    In production Caddy sets X-Real-IP on every request it proxies (see the
    Caddyfile): the visitor's address from Cloudflare's CF-Connecting-IP when
    the request came from a Cloudflare range, the connecting address when it
    did not. It overwrites any X-Real-IP the client sent, and gunicorn's port
    is never published, so only Caddy reaches Django.

    X-Forwarded-For is never read. Cloudflare appends to whatever the visitor
    sent, so its first entry is the visitor's to choose unless Caddy rewrites
    it. As a fallback it served no one -- nothing sends it in local dev -- and
    a Caddyfile edit that dropped X-Real-IP would have quietly let every
    request name its own per-IP bucket and ip_hash. Without X-Real-IP the
    socket address is used: one shared bucket is the safe way to be wrong.

    What comes back keys a visitor -- the per-IP limit and ChatLog's ip_hash
    -- so an IPv6 address is cut to its /64; see visitor().
    """
    real = request.META.get("HTTP_X_REAL_IP", "").strip()
    return visitor(real or request.META.get("REMOTE_ADDR", ""))


def visitor(address: str) -> str:
    """An IPv6 address as its /64 ("2001:db8:1:2::/64"), IPv4 as it is.

    An ISP hands each subscriber at least a /64, and the host picks its own
    address in it: privacy extensions rotate it daily, and a script can take
    a new one per request. Keyed on the full address, one IPv6 visitor could
    be as many per-IP buckets as they liked. One /64 is one subscriber.

    An IPv4-mapped address (::ffff:198.51.100.1) is an IPv4 visitor reached
    over an IPv6 socket, so it is keyed as that IPv4 address -- as a /64 it
    would put every such visitor in ::/64 together. Anything that does not
    parse is passed through: Caddy and the socket only ever send addresses.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if ip.version == 4:
        return address
    if ip.ipv4_mapped:
        return str(ip.ipv4_mapped)
    return str(ipaddress.ip_network((ip, 64), strict=False))
