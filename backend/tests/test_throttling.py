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


def test_the_global_cap_stops_everyone(db, settings, stub_graph):
    settings.CHAT_DAILY_CAP = 2
    api = APIClient()
    body = {"question": "q"}
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.1").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.2").status_code == 200
    assert api.post("/api/chat/", body, format="json", REMOTE_ADDR="198.51.100.3").status_code == 429


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
