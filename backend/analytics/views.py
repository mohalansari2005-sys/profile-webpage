import base64
import hmac
import logging
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.db import DatabaseError
from django.http import Http404, HttpResponse, UnreadablePostError
from django.shortcuts import render
from rest_framework import serializers, status
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework.fields import empty
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics import stats
from analytics.models import PageView
from chat.ip import client_ip
from chat.models import hash_ip
from chat.throttling import ChatRateThrottle

logger = logging.getLogger(__name__)

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
# from the beacon, and capping it keeps parsing cheap.
MAX_BODY = 8 * 1024
# Per field: about the longest URL that works in every browser, so a longer
# value is not from the beacon. The columns then cut further (path 200,
# source 100), so a merely long value is kept, shortened.
MAX_FIELD = 2000


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
    # The live site's exact origins only. CORS also lets *.vercel.app through
    # so previews can talk to the chat, but a preview's page views are QA, not
    # visitors (the chat logs them as synthetic for the same reason).
    return origin in settings.CORS_ALLOWED_ORIGINS


def country_of(request) -> str:
    # Only set when Cloudflare proxies the domain (DEPLOYMENT.md allows it).
    # "XX" is Cloudflare for "unknown"; "T1" (Tor) fails the letters check.
    code = request.META.get("HTTP_CF_IPCOUNTRY", "").strip().upper()
    return code if re.fullmatch(r"[A-Z]{2}", code) and code != "XX" else ""


class Text(serializers.CharField):
    """DRF's CharField, which already refuses the two things Postgres cannot
    store -- NUL, and a lone surrogate ("\\ud800" is valid JSON) -- either of
    which made the save a 500 with a logged traceback. Minus one habit: it
    reads a number as a string, and the beacon only ever sends strings, so 7
    is not a path."""

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class OptionalText(Text):
    """A field the page view can do without: a value that fails validation
    counts as not sent, instead of costing the whole visit."""

    def __init__(self, **kwargs):
        super().__init__(required=False, default="", allow_blank=True, max_length=MAX_FIELD,
                         **kwargs)

    def run_validation(self, data=empty):
        try:
            return super().run_validation(data)
        except serializers.ValidationError:
            return ""


class VisitSerializer(serializers.Serializer):
    # Blank is the root: normalise_path("") is "/".
    path = Text(allow_blank=True, max_length=MAX_FIELD)
    referrer = OptionalText()
    source = OptionalText()


class PlainTextJSONParser(JSONParser):
    """JSON sent as text/plain, the type navigator.sendBeacon can send
    cross-origin without a CORS preflight."""

    media_type = "text/plain"


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
    # Checked before anything reads the body. The parser reads no further than
    # this length, so it is also the cap on what is read.
    if declared_length(request) > MAX_BODY:
        return None
    try:
        body = request.data
    except (ParseError, UnsupportedMediaType, RecursionError):
        # Not JSON, not a type the beacon sends, or nested past Python's
        # recursion limit ("[[[[..." fits easily in MAX_BODY).
        return None
    visit = VisitSerializer(data=body)
    if not visit.is_valid():
        return None
    data = visit.validated_data

    # The site's own host covers internal navigation (the language toggle), so
    # "where did visitors come from" only lists other sites.
    own_hosts = {host_of(o) for o in settings.CORS_ALLOWED_ORIGINS}
    referrer = host_of(data["referrer"])
    return PageView(
        ip_hash=hash_ip(client_ip(request)),
        path=normalise_path(data["path"]),
        referrer_host="" if referrer in own_hosts else referrer[:200],
        source=data["source"][:100],
        country=country_of(request),
        device=device_of(ua),
        browser=browser_of(ua),
    )


class IgnoreAccept(DefaultContentNegotiation):
    """Both views below write their own answers (an empty 204, the page, a
    plain-text 401), so DRF only ever renders the throttle's 429. Its default
    negotiation would first refuse, with a 406, any client whose Accept header
    lacks */* -- breaking the beacon's always-204 and turning away a strict
    client that has the dashboard password. DRF's documented recipe for
    ignoring Accept, without its select_parser override: the beacon's parser
    is still picked by Content-Type."""

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class VisitView(APIView):
    """POST /api/visit/ -- one page view, sent by the frontend's beacon.

    The body is JSON, sent as text/plain by the beacon (PlainTextJSONParser)
    or as application/json by anything else.

    Every answer is an empty 204, stored or not, so a caller cannot learn what
    is filtered; only the throttle answers differently (429).
    """

    authentication_classes = []
    permission_classes = []
    content_negotiation_class = IgnoreAccept
    parser_classes = [JSONParser, PlainTextJSONParser]
    throttle_scope = "visit"
    # ChatRateThrottle is keyed on client_ip and reads the rate for the view's
    # own throttle_scope, so it serves here unchanged. The chat's
    # GlobalDailyThrottle is deliberately absent: it is the OpenAI spend cap,
    # and page views must never use it up.
    throttle_classes = [ChatRateThrottle]

    def post(self, request):
        # Neither failure below is worth a 500 and a logged traceback per
        # beacon: a lost page view is acceptable, and one warning line says why.
        try:
            view = page_view_from(request)
        except UnreadablePostError as exc:
            # The connection dropped mid-body, as when a tab closes on its
            # beacon. Nobody is waiting for the answer.
            logger.warning("Page view not read: %s", exc)
            view = None
        if view is not None:
            try:
                view.save()
            except DatabaseError as exc:
                # The first deploy serves before `migrate` has created the
                # table, and the database can be away for a moment. First line
                # only: the rest is the SQL statement.
                logger.warning("Page view not stored (%s): %s", type(exc).__name__,
                               str(exc).partition("\n")[0])
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
