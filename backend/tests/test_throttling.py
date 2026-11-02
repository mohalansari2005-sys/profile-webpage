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
