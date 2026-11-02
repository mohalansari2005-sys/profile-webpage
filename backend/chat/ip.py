def client_ip(request) -> str:
    """The one place the client address is derived. Never stored raw.

    Lives in its own module so views and throttling can both import it
    without importing each other.

    In production Caddy sets X-Real-IP on every request it proxies (see the
    Caddyfile): the visitor's address from Cloudflare's CF-Connecting-IP when
    the request came from a Cloudflare range, the connecting address when it
    did not. It overwrites any X-Real-IP the client sent, and gunicorn's port
    is never published, so only Caddy reaches Django. X-Forwarded-For is no
    substitute: Cloudflare appends to whatever the visitor sent, so its first
    entry is the visitor's to choose, and without Caddy's help every request
    looked like it came from a Cloudflare edge.

    Without Caddy (local dev) the forwarded header or the socket address is all
    there is.
    """
    real = request.META.get("HTTP_X_REAL_IP", "").strip()
    if real:
        return real
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
