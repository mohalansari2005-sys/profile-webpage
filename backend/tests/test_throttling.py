import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def stub_graph(monkeypatch):
    from chat import views

    class FakeGraph:
        def invoke(self, state):
            return {"answer": "ok", "refused": False, "sources": []}

    monkeypatch.setattr(views, "GRAPH", FakeGraph())


def test_per_ip_limit_returns_429(db, settings, stub_graph):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "2/min"}}
    api = APIClient()
    body = {"question": "q"}
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 429


def test_the_per_ip_limit_is_per_ip(db, settings, stub_graph):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    body = {"question": "q"}
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.2").status_code == 200


def test_behind_the_proxy_each_visitor_gets_their_own_bucket(db, settings, stub_graph):
    """Every proxied request reaches Django from Caddy. Keyed on that, or on
    Cloudflare's edge address, visitors who share an edge shared one limit."""
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    body = {"question": "q"}
    via_caddy = {"REMOTE_ADDR": "172.18.0.5", "HTTP_X_FORWARDED_FOR": "172.70.1.1"}
    assert api.post("/api/chat/", body, format="json", HTTP_X_REAL_IP="198.51.100.1",
                    **via_caddy).status_code == 200
    assert api.post("/api/chat/", body, format="json", HTTP_X_REAL_IP="198.51.100.2",
                    **via_caddy).status_code == 200


def test_a_spoofed_x_forwarded_for_does_not_buy_a_fresh_bucket(db, settings, stub_graph):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    body = {"question": "q"}
    for spoofed, expected in (("203.0.113.1", 200), ("203.0.113.2", 429)):
        r = api.post("/api/chat/", body, format="json", REMOTE_ADDR="172.18.0.5",
                     HTTP_X_REAL_IP="198.51.100.1",
                     HTTP_X_FORWARDED_FOR=f"{spoofed}, 172.70.1.1")
        assert r.status_code == expected


def test_the_global_cap_stops_everyone(db, settings, stub_graph):
    settings.CHAT_DAILY_CAP = 2
    api = APIClient()
    body = {"question": "q"}
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.2").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.3").status_code == 429


def test_one_client_over_its_limit_does_not_spend_the_global_cap(db, settings, stub_graph):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    settings.CHAT_DAILY_CAP = 2
    api = APIClient()
    body = {"question": "q"}
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 200
    for _ in range(5):
        assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 429
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.2").status_code == 200


def test_a_rejected_request_never_reaches_the_graph(db, settings, monkeypatch):
    from chat import views

    class Boom:
        def invoke(self, state):
            raise AssertionError("throttled requests must not spend quota")

    settings.CHAT_DAILY_CAP = 0
    monkeypatch.setattr(views, "GRAPH", Boom())
    r = APIClient().post("/api/chat/", {"question": "q"}, format="json")
    assert r.status_code == 429


def test_the_429_body_is_json_with_a_detail_key(db, settings, stub_graph):
    settings.CHAT_DAILY_CAP = 0
    r = APIClient().post("/api/chat/", {"question": "q"}, format="json")
    assert r.status_code == 429
    assert "detail" in r.json()


def test_the_daily_cap_429_says_it_is_the_daily_cap(db, settings, stub_graph):
    """A per-IP 429 clears in a minute; the daily cap's lasts until midnight.
    Shown the same "try again in a minute", a visitor retried all day."""
    settings.CHAT_DAILY_CAP = 0
    r = APIClient().post("/api/chat/", {"question": "q"}, format="json")
    assert r.status_code == 429
    assert r.json()["code"] == "daily_cap"


def test_a_per_ip_429_keeps_drf_s_body(db, settings, stub_graph):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    api.post("/api/chat/", {"question": "q"}, format="json")
    r = api.post("/api/chat/", {"question": "q"}, format="json")
    assert r.status_code == 429
    assert "code" not in r.json()
    assert "Expected available" in r.json()["detail"]


def test_only_a_valid_chat_turn_spends_the_daily_cap(db, settings, stub_graph):
    """GET and HEAD (405), a plain OPTIONS and a body that fails validation
    (400) cost nothing upstream. Counted, ~200 of them from a scanner or an
    uptime check closed the chat for every visitor until the next day."""
    settings.CHAT_DAILY_CAP = 1
    api = APIClient()
    assert api.get("/api/chat/", REMOTE_ADDR="198.51.100.1").status_code == 405
    assert api.head("/api/chat/", REMOTE_ADDR="198.51.100.2").status_code == 405
    assert api.options("/api/chat/", REMOTE_ADDR="198.51.100.3").status_code == 200
    assert api.post("/api/chat/", {}, format="json", REMOTE_ADDR="198.51.100.4").status_code == 400
    body = {"question": "q"}
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.5").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.6").status_code == 429


def test_other_methods_leave_the_per_ip_budget_alone(db, settings, stub_graph):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    for _ in range(3):
        assert api.get("/api/chat/").status_code == 405
    assert api.post("/api/chat/", {"question": "q"}, format="json").status_code == 200


def test_an_invalid_post_still_counts_against_the_per_ip_limit(db, settings, stub_graph):
    """The per-IP limit stays in front of every POST, valid or not, so a
    client cannot hammer the endpoint for free either."""
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    assert api.post("/api/chat/", {}, format="json").status_code == 400
    assert api.post("/api/chat/", {}, format="json").status_code == 429


def test_an_authorization_header_is_ignored_not_checked(db, settings, stub_graph, monkeypatch):
    """The API is anonymous. DRF's default BasicAuthentication still looked up
    a user and ran a million-round password hash for any request carrying the
    header -- before any throttle, so nothing counted or limited it."""
    from django.contrib.auth.backends import ModelBackend

    def no_auth(*a, **k):
        raise AssertionError("an anonymous API must not authenticate")

    monkeypatch.setattr(ModelBackend, "authenticate", no_auth)
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"chat": "1/min"}}
    api = APIClient()
    basic = {"HTTP_AUTHORIZATION": "Basic bm9ib2R5Ong="}  # nobody:x
    assert api.post("/api/chat/", {"question": "q"}, format="json", **basic).status_code == 200
    assert api.post("/api/chat/", {"question": "q"}, format="json", **basic).status_code == 429


def test_a_refund_never_takes_the_counter_below_zero():
    """Two refunds racing for one slot, or one after the key expired, must not
    grant slots past the cap."""
    from types import SimpleNamespace

    from chat.throttling import GlobalDailyThrottle

    cache.set("chat:daily:test", 1)
    request = SimpleNamespace(chat_daily_key="chat:daily:test")
    GlobalDailyThrottle.refund(request)
    GlobalDailyThrottle.refund(request)
    assert cache.get("chat:daily:test") == 0
    GlobalDailyThrottle.refund(SimpleNamespace(chat_daily_key="chat:daily:gone"))
    GlobalDailyThrottle.refund(SimpleNamespace())
