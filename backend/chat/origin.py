from urllib.parse import urlsplit

from django.conf import settings


def live_site(origin: str) -> bool:
    """True when `origin` is one of CORS_ALLOWED_ORIGINS: the live site.

    Compared the way django-cors-headers compares them -- scheme and host
    after urlsplit, which drops a leading space and lower-cases the scheme --
    not as exact strings. A value such as "https://a.stream, https://www.a.stream"
    keeps the chat working through CORS; an exact match would then quietly log
    every real question as synthetic and drop every real page view.

    The *.vercel.app pattern CORS also allows is not the live site: previews
    are QA, not visitors. No Origin, or "null", is never the live site.
    """
    try:
        url = urlsplit(origin)
    except ValueError:  # e.g. an unbalanced IPv6 bracket
        return False
    if not (url.scheme and url.netloc):
        return False
    return any((listed.scheme, listed.netloc) == (url.scheme, url.netloc)
               for listed in map(urlsplit, settings.CORS_ALLOWED_ORIGINS))
