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
    """
    real = request.META.get("HTTP_X_REAL_IP", "").strip()
    return real or request.META.get("REMOTE_ADDR", "")
