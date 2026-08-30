def client_ip(request) -> str:
    """The one place the client address is derived. Never stored raw.

    Lives in its own module so views and throttling can both import it
    without importing each other.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
