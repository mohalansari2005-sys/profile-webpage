import json
import logging
from datetime import date

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

CHROME_DESKTOP = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SAFARI_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
                 "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def site(settings):
    """The frontend's origin, on the same allow-list the chat's CORS uses."""
    settings.CORS_ALLOWED_ORIGINS = ["https://example.dev"]
    return "https://example.dev"


def beacon(api, body, ua=CHROME_DESKTOP, **extra):
    """POST the way navigator.sendBeacon does: a JSON string sent as text/plain."""
    raw = body if isinstance(body, str) else json.dumps(body)
    headers = {"HTTP_USER_AGENT": ua} if ua is not None else {}
    return api.post("/api/visit/", data=raw, content_type="text/plain;charset=UTF-8",
                    **headers, **extra)


def stored():
    from analytics.models import PageView

    return list(PageView.objects.all())


def test_a_visit_is_stored_with_a_hashed_ip(db, api):
    from chat.models import hash_ip

    r = beacon(api, {"path": "/ar"}, REMOTE_ADDR="203.0.113.9")
    assert r.status_code == 204
    [view] = stored()
    assert view.ip_hash == hash_ip("203.0.113.9")
    assert "203.0.113.9" not in view.ip_hash
    assert view.path == "/ar"


def test_the_ip_hash_matches_the_chat_logs_key_behind_a_proxy(db, api):
    """Caddy names the visitor in X-Real-IP (Cloudflare's CF-Connecting-IP,
    believed only from Cloudflare's ranges); a client-sent X-Forwarded-For is
    never read."""
    from chat.models import hash_ip

    beacon(api, {"path": "/"}, HTTP_X_REAL_IP="198.51.100.7",
           HTTP_X_FORWARDED_FOR="203.0.113.66", REMOTE_ADDR="10.0.0.1")
    assert stored()[0].ip_hash == hash_ip("198.51.100.7")


@pytest.mark.parametrize("raw, normalised", [
    ("/", "/"),
    ("", "/"),
    ("ar", "/ar"),
    ("/ar/", "/ar"),
    ("/ar?utm_source=x", "/ar"),
    ("/#about", "/"),
    ("/ar/#work", "/ar"),
    ("/" + "x" * 300, "/" + "x" * 199),
])
def test_the_path_is_normalised(db, api, raw, normalised):
    beacon(api, {"path": raw})
    assert stored()[0].path == normalised


def test_device_browser_country_and_source_are_derived(db, api):
    beacon(api, {"path": "/", "source": "linkedin"}, ua=SAFARI_IPHONE, HTTP_CF_IPCOUNTRY="sa")
    [view] = stored()
    assert (view.device, view.browser, view.country, view.source) == (
        "mobile", "Safari", "SA", "linkedin")


@pytest.mark.parametrize("ua, device, browser", [
    (CHROME_DESKTOP, "desktop", "Chrome"),
    (SAFARI_IPHONE, "mobile", "Safari"),
    ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
     "Version/17.0 Mobile/15E148 Safari/604.1", "tablet", "Safari"),
    ("Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) "
     "SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36", "mobile", "Samsung"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0", "desktop", "Edge"),
    ("Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
     "desktop", "Firefox"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/130.0.0.0 Safari/537.36 OPR/115.0.0.0", "desktop", "Other"),
    # A phone brand with "bot" in its name: counted, not filtered as a bot.
    ("Mozilla/5.0 (Linux; Android 10; CUBOT X30) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/120.0.0.0 Mobile Safari/537.36", "mobile", "Chrome"),
])
def test_the_user_agent_is_reduced_to_coarse_families(db, api, ua, device, browser):
    beacon(api, {"path": "/"}, ua=ua)
    [view] = stored()
    assert (view.device, view.browser) == (device, browser)


def test_the_user_agent_string_itself_is_not_stored(db, api):
    from analytics.models import PageView

    beacon(api, {"path": "/"})
    row = PageView.objects.values().get()
    assert not any("Mozilla" in str(value) for value in row.values())


def test_country_is_blank_without_a_usable_cloudflare_header(db, api):
    beacon(api, {"path": "/"})
    beacon(api, {"path": "/"}, HTTP_CF_IPCOUNTRY="XX")  # Cloudflare's "unknown"
    beacon(api, {"path": "/"}, HTTP_CF_IPCOUNTRY="<b>")
    assert [v.country for v in stored()] == ["", "", ""]


def test_an_external_referrer_is_kept_as_its_host(db, api, site):
    beacon(api, {"path": "/", "referrer": "https://www.linkedin.com/in/someone?trk=x"},
           HTTP_ORIGIN=site)
    assert stored()[0].referrer_host == "www.linkedin.com"


@pytest.mark.parametrize("referrer", [
    "",
    "https://example.dev/?lang=en",  # the language toggle: the site's own host
    "not a url",
])
def test_internal_or_missing_referrer_is_blank(db, api, site, referrer):
    beacon(api, {"path": "/ar", "referrer": referrer}, HTTP_ORIGIN=site)
    assert stored()[0].referrer_host == ""


def test_the_sites_own_host_is_blank_even_without_an_origin_header(db, api, site):
    beacon(api, {"path": "/", "referrer": f"{site}/ar"})
    assert stored()[0].referrer_host == ""


def test_non_string_fields_are_treated_as_absent(db, api):
    beacon(api, {"path": "/", "referrer": 42, "source": ["x"]})
    [view] = stored()
    assert (view.referrer_host, view.source) == ("", "")


def test_a_long_source_is_truncated(db, api):
    beacon(api, {"path": "/", "source": "s" * 500})
    assert stored()[0].source == "s" * 100


@pytest.mark.parametrize("ua", [
    None,
    "",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "HeadlessChrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; moto g power (2022)) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 Chrome-Lighthouse",
    "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) SkypeUriPreview Preview/0.5",
    "curl/8.7.1",
    "Wget/1.21.4",
    "python-requests/2.32.3",
])
def test_bots_and_scripts_are_ignored(db, api, ua):
    r = beacon(api, {"path": "/"}, ua=ua)
    assert r.status_code == 204
    assert stored() == []


def test_a_foreign_origin_is_ignored(db, api, site):
    r = beacon(api, {"path": "/"}, HTTP_ORIGIN="https://evil.example")
    assert r.status_code == 204
    assert stored() == []


def test_the_live_sites_origin_is_stored(db, api, site):
    beacon(api, {"path": "/"}, HTTP_ORIGIN=site)
    assert len(stored()) == 1


@pytest.mark.parametrize("listed", [
    " https://www.example.dev",  # CORS_ORIGINS="https://example.dev, https://www.example.dev"
    "HTTPS://www.example.dev",
])
def test_the_live_site_is_matched_the_way_cors_matches_it(db, api, settings, listed):
    # django-cors-headers compares scheme and host after urlsplit, so either
    # spelling keeps the chat working; an exact string match then dropped
    # every real page view without a word.
    settings.CORS_ALLOWED_ORIGINS = ["https://example.dev", listed]
    beacon(api, {"path": "/"}, HTTP_ORIGIN="https://www.example.dev")
    assert len(stored()) == 1


def test_a_null_origin_is_not_the_live_site(db, api, settings):
    # A sandboxed page or a local file sends "Origin: null". A blank entry
    # ("a, ,b" in CORS_ORIGINS) parses to no scheme and no host either, and
    # must not make it count.
    settings.CORS_ALLOWED_ORIGINS = ["https://example.dev", " "]
    beacon(api, {"path": "/"}, HTTP_ORIGIN="null")
    assert stored() == []


def test_a_preview_deployment_is_ignored(db, api, site):
    # CORS lets *.vercel.app talk to the chat; its page views are QA, not
    # visitors, so the beacon takes only the live site's listed origins.
    r = beacon(api, {"path": "/"}, HTTP_ORIGIN="https://profile-webpage-git-feat-x.vercel.app")
    assert r.status_code == 204
    assert stored() == []


@pytest.mark.parametrize("body", [
    "not json",
    "",
    "[1, 2]",
    json.dumps({"referrer": "https://x.example"}),  # no path
    json.dumps({"path": 7}),
    json.dumps({"path": None}),
])
def test_a_malformed_body_is_ignored(db, api, body):
    r = beacon(api, body)
    assert r.status_code == 204
    assert stored() == []


# Raw JSON text, so the escapes reach the server as a browser would send them.
# Postgres refuses NUL in text, and a lone surrogate has no UTF-8 form; saved,
# either was a 500 and a logged traceback on every hit. DRF's CharField
# refuses both, so a bad path drops the beacon and a bad optional field is
# treated as not sent.
@pytest.mark.parametrize("body", [
    r'{"path": "/\u0000ar"}',
    r'{"path": "/ar\ud800"}',
])
def test_a_path_postgres_cannot_store_is_ignored_not_a_500(db, api, body):
    r = beacon(api, body)
    assert r.status_code == 204
    assert stored() == []


@pytest.mark.parametrize("body, field", [
    (r'{"path": "/", "source": "a\u0000b"}', "source"),
    (r'{"path": "/", "referrer": "https://a\u0000b.example/"}', "referrer_host"),
    (r'{"path": "/", "source": "x\udfff"}', "source"),
])
def test_an_optional_field_postgres_cannot_store_is_dropped_not_a_500(db, api, body, field):
    r = beacon(api, body)
    assert r.status_code == 204
    assert getattr(stored()[0], field) == ""


def test_an_overlong_path_is_ignored_and_an_overlong_source_dropped(db, api):
    from analytics.views import MAX_FIELD

    beacon(api, {"path": "/" + "x" * MAX_FIELD})
    assert stored() == []
    beacon(api, {"path": "/ar", "source": "s" * (MAX_FIELD + 1)})
    [view] = stored()
    assert (view.path, view.source) == ("/ar", "")


def test_deeply_nested_json_is_ignored_not_a_500(db, api):
    # About as deep as the body cap allows. CPython's C scanner parses it
    # (checked on 3.12 and 3.14), so this is a smoke test: it is
    # dropped because a list is not a visit. The test below forces the
    # RecursionError a build without the C scanner would raise.
    r = beacon(api, "[" * 4000 + "]" * 4000)
    assert r.status_code == 204
    assert stored() == []


def test_json_nested_past_the_recursion_limit_is_ignored_not_a_500(db, api, monkeypatch):
    from analytics import views

    def too_deep(*args, **kwargs):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(views.BeaconJSONParser, "parse", too_deep)
    r = beacon(api, {"path": "/"})
    assert r.status_code == 204
    assert stored() == []


@pytest.mark.parametrize("body", [
    "path=/ar",
    # Valid JSON, so this one fails if the JSON parser is picked whatever the
    # Content-Type (as DRF's recipe for ignoring Accept would pick it).
    json.dumps({"path": "/ar"}),
])
def test_a_form_body_is_ignored(db, api, body):
    r = api.post("/api/visit/", body, content_type="application/x-www-form-urlencoded",
                 HTTP_USER_AGENT=CHROME_DESKTOP)
    assert r.status_code == 204
    assert stored() == []


@pytest.mark.parametrize("content_type", [
    "text/plain; charset=utf-16",
    "text/plain; charset=rot13",
    "text/plain; charset=zlib",
    "text/plain; charset=bz2",
    "application/json; charset=rot13",
])
def test_the_charset_in_the_content_type_is_ignored(db, api, content_type):
    # The beacon only ever sends UTF-8. DRF decodes with the named charset,
    # and before 3.18.2 it took any codec: rot13, zlib and bz2 raised errors
    # that were a 500 per beacon. Read as bytes, the body is the same visit.
    r = api.post("/api/visit/", json.dumps({"path": "/ar"}), content_type=content_type,
                 HTTP_USER_AGENT=CHROME_DESKTOP)
    assert r.status_code == 204
    assert [v.path for v in stored()] == ["/ar"]


def test_a_body_too_big_for_django_is_ignored_without_reading_it(db, api, settings):
    # Past DATA_UPLOAD_MAX_MEMORY_SIZE, reading request.body raises and Django
    # answers 400; the declared length has to turn it away first.
    big = {"path": "/", "source": "x" * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)}
    r = beacon(api, big)
    assert r.status_code == 204
    assert stored() == []


def test_an_accept_header_without_a_wildcard_still_gets_the_204(db, api):
    r = beacon(api, {"path": "/"}, HTTP_ACCEPT="text/html")
    assert r.status_code == 204
    assert len(stored()) == 1


def test_a_json_content_type_is_accepted_too(db, api):
    r = api.post("/api/visit/", {"path": "/ar"}, format="json", HTTP_USER_AGENT=CHROME_DESKTOP)
    assert r.status_code == 204
    assert stored()[0].path == "/ar"


def test_every_answer_is_an_empty_204(db, api):
    responses = [
        beacon(api, {"path": "/"}),  # stored
        beacon(api, {"path": "/"}, ua="curl/8.7.1"),  # bot
        beacon(api, {"path": "/"}, HTTP_ORIGIN="https://evil.example"),  # foreign origin
        beacon(api, "{"),  # bad JSON
    ]
    assert [r.status_code for r in responses] == [204] * 4
    assert [r.content for r in responses] == [b""] * 4


def _quiet_warning(caplog, text):
    """One WARNING from the view saying `text`, without a traceback, and no
    ERROR (a 500 is logged at ERROR by django.request)."""
    ours = [r for r in caplog.records if r.name == "analytics.views"]
    assert [r.levelno for r in ours] == [logging.WARNING]
    assert text in ours[0].getMessage()
    assert ours[0].exc_info is None
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.parametrize("error", [
    ConnectionResetError(54, "Connection reset by peer"),
    OSError("request data read error"),  # what gunicorn raises for a short body
])
def test_a_dropped_connection_is_a_204_and_one_warning(db, api, monkeypatch, caplog, error):
    """A beacon sent as the tab closes can lose its connection mid-body;
    Django turns that into UnreadablePostError when the body is read."""
    from django.core.handlers.wsgi import LimitedStream

    def drop(*args, **kwargs):
        raise error

    monkeypatch.setattr(LimitedStream, "read", drop)
    r = beacon(api, {"path": "/"})
    assert r.status_code == 204
    assert stored() == []
    _quiet_warning(caplog, "Page view not read")


@pytest.mark.parametrize("error", [
    # The first deploy serves before `migrate` has created the table.
    'relation "analytics_pageview" does not exist\nLINE 1: INSERT INTO "analytics_pageview" ...',
    "connection to server failed: Connection refused",
])
def test_a_database_error_is_a_204_and_one_warning(db, api, monkeypatch, caplog, error):
    from django.db import OperationalError, ProgrammingError

    from analytics.models import PageView

    exc = (ProgrammingError if "relation" in error else OperationalError)(error)

    def fail(self, *args, **kwargs):
        raise exc

    monkeypatch.setattr(PageView, "save", fail)
    r = beacon(api, {"path": "/"})
    assert (r.status_code, r.content) == (204, b"")
    _quiet_warning(caplog, error.partition("\n")[0])
    assert "LINE 1" not in caplog.text


def test_get_is_not_allowed(db, api):
    assert api.get("/api/visit/").status_code == 405


def test_the_per_ip_limit_returns_429(db, api, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"visit": "2/min"}}
    codes = [beacon(api, {"path": "/"}, REMOTE_ADDR="198.51.100.1").status_code
             for _ in range(3)]
    assert codes == [204, 204, 429]
    assert beacon(api, {"path": "/"}, REMOTE_ADDR="198.51.100.2").status_code == 204
    assert len(stored()) == 3


def test_the_beacon_never_spends_the_chats_daily_cap(db, api, settings):
    settings.CHAT_DAILY_CAP = 0
    assert beacon(api, {"path": "/"}).status_code == 204
    assert len(stored()) == 1
    assert cache.get(f"chat:daily:{date.today().isoformat()}") is None
