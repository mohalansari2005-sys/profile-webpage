import base64
import hmac
import json
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics import stats
from analytics.models import PageView
from chat.ip import client_ip
from chat.models import hash_ip
from chat.throttling import ChatRateThrottle

# Best-effort, not security: a script that lies about its User-Agent is still
# counted. This catches crawlers, link-preview fetchers, audit tools and the
# usual HTTP libraries, which between them are most non-human traffic.
# "(?<!cu)": Cubot is an Android phone brand, and its model names ("CUBOT X30")
# would otherwise read as a bot.
BOT_UA = re.compile(
    r"(?<!cu)bot|crawl|spider|slurp|headless|lighthouse|preview|curl|wget|python|"
    r"http-?client|okhttp|go-http|java/|node-fetch|axios|scrapy|facebookexternalhit",
    re.IGNORECASE,
)

# Checked in order: Edge, Samsung and Opera all also claim "Chrome", and every
# Chromium browser also claims "Safari".
BROWSERS = (
    ("Edge", ("edg/", "edge/", "edga/", "edgios/")),
    ("Samsung", ("samsungbrowser/",)),
    ("Other", ("opr/", "opera")),
    ("Firefox", ("firefox/", "fxios/")),
    ("Chrome", ("chrome/", "crios/", "chromium/")),
    ("Safari", ("safari/",)),
)

# Generous for a path, a referrer URL and a source; anything bigger is not
# from the beacon, and capping it keeps json.loads cheap.
MAX_BODY = 8 * 1024


def device_of(ua: str) -> str:
    ua = ua.lower()
    # Android tablets drop "Mobile" from the UA; iPads since iPadOS 13 claim to
    # be a Mac and count as desktop, which is what their layout is.
    if "ipad" in ua or "tablet" in ua or ("android" in ua and "mobile" not in ua):
        return "tablet"
    if "mobi" in ua or "iphone" in ua or "ipod" in ua:
        return "mobile"
    return "desktop"


def browser_of(ua: str) -> str:
    ua = ua.lower()
    for name, marks in BROWSERS:
        if any(mark in ua for mark in marks):
            return name
    return "Other"


def normalise_path(raw: str) -> str:
    """"/ar/?utm_source=x#work" -> "/ar", so one page is one row in the table."""
    path = re.split(r"[?#]", raw, maxsplit=1)[0].strip()
    return ("/" + path.strip("/"))[:200]


def host_of(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:  # e.g. an unbalanced IPv6 bracket
        return ""


def origin_allowed(origin: str) -> bool:
    # The chat's CORS allow-list, read from the same settings corsheaders uses
    # and matched the way it matches them.
    return origin in settings.CORS_ALLOWED_ORIGINS or any(
        re.match(pattern, origin) for pattern in settings.CORS_ALLOWED_ORIGIN_REGEXES)


def country_of(request) -> str:
    # Only set when Cloudflare proxies the domain (DEPLOYMENT.md allows it).
    # "XX" is Cloudflare for "unknown"; "T1" (Tor) fails the letters check.
    code = request.META.get("HTTP_CF_IPCOUNTRY", "").strip().upper()
    return code if re.fullmatch(r"[A-Z]{2}", code) and code != "XX" else ""


def text(value) -> str:
    """A visitor-supplied string made safe to store, or "" if it is not a string.

    The chat gets this from DRF's CharField; this view reads the body itself,
    so it cleans the two things Postgres cannot store: NUL, which it refuses
    in text, and a lone surrogate ("\\ud800" is valid JSON), which has no UTF-8
    form. Either would make the save a 500 with a logged traceback.
    """
    if not isinstance(value, str):
        return ""
    return value.replace("\x00", "").encode("utf-8", "replace").decode("utf-8").strip()


def declared_length(request) -> int:
    try:
        return int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return 0


def page_view_from(request) -> PageView | None:
    """The row this beacon describes, or None when it should not be counted."""
    ua = request.META.get("HTTP_USER_AGENT", "")
    if not ua or BOT_UA.search(ua):
        return None
    origin = request.META.get("HTTP_ORIGIN", "")
    if origin and not origin_allowed(origin):
        return None
    # The declared length first: reading request.body loads all of it, and
    # past DATA_UPLOAD_MAX_MEMORY_SIZE Django answers 400 instead of our 204.
    # The length of what was actually read stays as the backstop.
    if declared_length(request) > MAX_BODY or len(request.body) > MAX_BODY:
        return None
    try:
        body = json.loads(request.body)
    except (ValueError, RecursionError):  # ValueError covers bad JSON and bad UTF-8
        return None
    if not isinstance(body, dict) or not isinstance(body.get("path"), str):
        return None

    # The site's own host covers internal navigation (the language toggle), so
    # "where did visitors come from" only lists other sites.
    own_hosts = {host_of(o) for o in settings.CORS_ALLOWED_ORIGINS} | {host_of(origin)}
    referrer = host_of(text(body.get("referrer")))
    return PageView(
        ip_hash=hash_ip(client_ip(request)),
        path=normalise_path(text(body["path"])),
        referrer_host="" if referrer in own_hosts else referrer[:200],
        source=text(body.get("source"))[:100],
        country=country_of(request),
        device=device_of(ua),
        browser=browser_of(ua),
    )


class IgnoreAccept(BaseContentNegotiation):
    """Both views below write their own answers (an empty 204, the page, a
    plain-text 401), so DRF only ever renders the throttle's 429. Its default
    negotiation would first refuse, with a 406, any client whose Accept header
    lacks */* -- breaking the beacon's always-204 and turning away a strict
    client that has the dashboard password. DRF's documented recipe for
    ignoring Accept."""

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class VisitView(APIView):
    """POST /api/visit/ -- one page view, sent by the frontend's beacon.

    The body is JSON sent as text/plain, the type navigator.sendBeacon can send
    cross-origin without a CORS preflight. DRF has no parser for that, so the
    view reads request.body itself instead of request.data.

    Every answer is an empty 204, stored or not, so a caller cannot learn what
    is filtered; only the throttle answers differently (429).
    """

    authentication_classes = []
    permission_classes = []
    content_negotiation_class = IgnoreAccept
    throttle_scope = "visit"
    # ChatRateThrottle is keyed on client_ip and reads the rate for the view's
    # own throttle_scope, so it serves here unchanged. The chat's
    # GlobalDailyThrottle is deliberately absent: it is the OpenAI spend cap,
    # and page views must never use it up.
    throttle_classes = [ChatRateThrottle]

    def post(self, request):
        view = page_view_from(request)
        if view is not None:
            view.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


def password_ok(request) -> bool:
    scheme, _, credentials = request.META.get("HTTP_AUTHORIZATION", "").partition(" ")
    if scheme.lower() != "basic":
        return False
    try:
        decoded = base64.b64decode(credentials.strip(), validate=True).decode("utf-8")
    except ValueError:  # binascii.Error and UnicodeDecodeError both subclass it
        return False
    _user, colon, given = decoded.partition(":")
    if not colon:
        return False
    # Bytes, because compare_digest rejects a str with non-ASCII characters.
    return hmac.compare_digest(given.encode(), settings.DASHBOARD_PASSWORD.encode())


class DashboardView(APIView):
    """GET /dashboard/ -- the owner's page. HTTP Basic, password only.

    An APIView, though it renders HTML, for one reason: it reuses the chat's
    per-IP throttle, which is what makes password guessing slow.
    """

    # Empty, not DRF's default: BasicAuthentication would read the same
    # Authorization header, look for a Django user and reject the request.
    authentication_classes = []
    permission_classes = []
    content_negotiation_class = IgnoreAccept
    throttle_scope = "dashboard"
    throttle_classes = [ChatRateThrottle]
    http_method_names = ["get", "head"]

    def dispatch(self, request, *args, **kwargs):
        # Raised before DRF takes over, so a disabled dashboard gets Django's
        # own 404: the same answer as a URL that does not exist.
        if not settings.DASHBOARD_PASSWORD:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        # On every answer, 401 and 429 included.
        response["Cache-Control"] = "no-store"
        response["X-Robots-Tag"] = "noindex"
        return response

    def get(self, request):
        if not password_ok(request):
            response = HttpResponse("Password required.\n", status=401,
                                    content_type="text/plain; charset=utf-8")
            response["WWW-Authenticate"] = 'Basic realm="dashboard"'
            return response
        days = stats.parse_days(request.GET.get("days"))
        return render(request, "analytics/dashboard.html",
                      {"stats": stats.collect(days), "ranges": stats.RANGES})
