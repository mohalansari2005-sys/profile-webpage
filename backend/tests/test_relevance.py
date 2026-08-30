def _fake(in_scope, reason=""):
    from chat.graph.nodes.relevance import Relevance

    return lambda *a, **k: (Relevance(in_scope=in_scope, reason=reason), {})


def test_in_scope_question_passes(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", _fake(True))
    out = node.relevance({"condensed": "what did he build at Majara"})
    assert out["in_scope"] is True


def test_out_of_scope_question_is_marked_with_a_reason(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", _fake(False, "asks about the weather"))
    out = node.relevance({"condensed": "what's the weather in Riyadh"})
    assert out["in_scope"] is False
    assert out["refusal_reason"] == "asks about the weather"


def test_an_unparseable_response_fails_closed(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", lambda *a, **k: (None, {}))
    out = node.relevance({"condensed": "anything"})
    assert out["in_scope"] is False


def test_the_gate_uses_the_fast_model(monkeypatch):
    from chat.graph.nodes import relevance as node
    from chat.graph.nodes.relevance import Relevance

    seen = {}

    def fake(prompt, schema, *, fast=False):
        seen["fast"] = fast
        return Relevance(in_scope=True, reason="ok"), {}

    monkeypatch.setattr(node, "structured", fake)
    node.relevance({"condensed": "q"})
    assert seen["fast"] is True


def test_routing_follows_the_gate():
    from chat.graph.nodes.relevance import route

    assert route({"in_scope": True}) == "retrieve"
    assert route({"in_scope": False}) == "log"
