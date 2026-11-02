import json
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
    from chat.models import hash_ip

    beacon(api, {"path": "/"}, HTTP_X_FORWARDED_FOR="198.51.100.7, 10.0.0.1",
           REMOTE_ADDR="10.0.0.1")
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


@pytest.mark.parametrize("origin", [
    "https://example.dev",
    "https://profile-webpage-git-feat-x.vercel.app",  # previews, via the regex
])
def test_an_allowed_origin_is_stored(db, api, site, origin):
    beacon(api, {"path": "/"}, HTTP_ORIGIN=origin)
    assert len(stored()) == 1


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
