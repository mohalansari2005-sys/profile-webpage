def _fake(subject, reason=""):
    from chat.graph.nodes.relevance import Relevance

    return lambda *a, **k: (Relevance(subject=subject, reason=reason), {})


def test_in_scope_question_passes(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", _fake("mohammed"))
    out = node.relevance({"condensed": "what did he build at Majara"})
    assert out["in_scope"] is True


def test_out_of_scope_question_is_marked_with_a_reason(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", _fake("general", "asks about the weather"))
    out = node.relevance({"condensed": "what's the weather in Riyadh"})
    assert out["in_scope"] is False
    # The category leads, so a month of refusals can be grouped without reading
    # the prose one row at a time.
    assert out["refusal_reason"] == "general: asks about the weather"


def test_an_unparseable_response_fails_closed(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", lambda *a, **k: (None, {}))
    out = node.relevance({"condensed": "anything"})
    assert out["in_scope"] is False
    assert out["refusal_reason"] == "scope check failed"


def test_an_api_failure_is_distinguished_from_an_unparseable_response(monkeypatch):
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", lambda *a, **k: (None, {"api_error": True}))
    out = node.relevance({"condensed": "anything"})
    assert out["in_scope"] is False
    assert out["refusal_reason"] == "generation unavailable"


def test_the_gate_uses_the_fast_model(monkeypatch):
    from chat.graph.nodes import relevance as node
    from chat.graph.nodes.relevance import Relevance

    seen = {}

    def fake(prompt, schema, *, fast=False):
        seen["fast"] = fast
        return Relevance(subject="mohammed", reason="ok"), {}

    monkeypatch.setattr(node, "structured", fake)
    node.relevance({"condensed": "q"})
    assert seen["fast"] is True


def test_routing_follows_the_gate():
    from chat.graph.nodes.relevance import route

    assert route({"in_scope": True}) == "retrieve"
    assert route({"in_scope": False}) == "log"


def test_an_unrecognised_name_is_treated_as_one_of_his(monkeypatch):
    """The production bug: the gate had never heard of Majara, so it refused
    "What is Majara?" as unrelated to Mohammed -- his own employer. An unknown
    name now reaches retrieval, and generate refuses if the corpus lacks it."""
    from chat.graph.nodes import relevance as node

    monkeypatch.setattr(node, "structured", _fake("unknown_name", "never heard of it"))
    assert node.relevance({"condensed": "what is Majara"})["in_scope"] is True


def test_prompt_injection_and_other_people_are_refused(monkeypatch):
    from chat.graph.nodes import relevance as node

    for subject in ("instruction_override", "other_person", "general"):
        monkeypatch.setattr(node, "structured", _fake(subject, "nope"))
        out = node.relevance({"condensed": "..."})
        assert out["in_scope"] is False
        assert out["refusal_reason"].startswith(subject)


def test_scope_is_decided_in_python_not_by_the_model(monkeypatch):
    """No in_scope field exists for the model to get wrong: it names a subject
    and IN_SCOPE maps that to a decision."""
    from chat.graph.nodes.relevance import IN_SCOPE, Relevance

    assert "in_scope" not in Relevance.model_fields
    assert IN_SCOPE == {"mohammed", "unknown_name"}
