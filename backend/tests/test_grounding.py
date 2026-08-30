RETRIEVED = [
    {"chunk_id": "exp-majara#summary", "record_id": "exp-majara",
     "title": "Product Engineering intern", "text": "Built Python services."},
    {"chunk_id": "exp-seet#summary", "record_id": "exp-seet",
     "title": "Business Development", "text": "Ran client meetings."},
]


def _answer(**kw):
    from chat.graph.nodes.generate import Answer

    return Answer(**{"answer": "a", "used_chunk_ids": [], "sufficient": True, **kw})


def _fake(answer):
    return lambda *a, **k: (answer, {"prompt_tokens": 10, "completion_tokens": 5})


def test_a_grounded_answer_passes_through(monkeypatch):
    from chat.graph.nodes import generate as node

    monkeypatch.setattr(node, "structured", _fake(_answer(
        answer="He built Python backend services.",
        used_chunk_ids=["exp-majara#summary"],
    )))
    out = node.generate({"condensed": "q", "retrieved": RETRIEVED})
    assert out["refused"] is False
    assert out["answer"] == "He built Python backend services."
    assert out["sources"] == [{"record_id": "exp-majara", "title": "Product Engineering intern"}]


def test_an_invented_chunk_id_becomes_a_refusal(monkeypatch):
    from chat.graph.nodes import generate as node

    monkeypatch.setattr(node, "structured", _fake(_answer(
        answer="He founded a startup in Dubai.",
        used_chunk_ids=["exp-majara#summary", "exp-invented#summary"],
    )))
    out = node.generate({"condensed": "q", "retrieved": RETRIEVED})
    assert out["refused"] is True
    assert out["refusal_reason"] == "ungrounded citation"
    assert "startup in Dubai" not in out["answer"]


def test_sufficient_false_becomes_a_refusal(monkeypatch):
    from chat.graph.nodes import generate as node

    monkeypatch.setattr(node, "structured", _fake(_answer(
        answer="I think so?", used_chunk_ids=["exp-majara#summary"], sufficient=False,
    )))
    out = node.generate({"condensed": "q", "retrieved": RETRIEVED})
    assert out["refused"] is True
    assert out["refusal_reason"] == "insufficient context"


def test_an_unparseable_response_becomes_a_refusal(monkeypatch):
    from chat.graph.nodes import generate as node

    monkeypatch.setattr(node, "structured", lambda *a, **k: (None, {}))
    out = node.generate({"condensed": "q", "retrieved": RETRIEVED})
    assert out["refused"] is True
    assert out["refusal_reason"] == "unparseable response"


def test_an_api_failure_is_distinguished_from_an_unparseable_response(monkeypatch):
    from chat.graph.nodes import generate as node

    monkeypatch.setattr(node, "structured", lambda *a, **k: (None, {"api_error": True}))
    out = node.generate({"condensed": "q", "retrieved": RETRIEVED})
    assert out["refused"] is True
    assert out["refusal_reason"] == "generation unavailable"


def test_empty_retrieval_refuses_without_calling_the_model(monkeypatch):
    from chat.graph.nodes import generate as node

    def boom(*a, **k):
        raise AssertionError("must not generate with nothing retrieved")

    monkeypatch.setattr(node, "structured", boom)
    out = node.generate({"condensed": "q", "retrieved": []})
    assert out["refused"] is True


def test_sources_are_deduplicated_by_record(monkeypatch):
    from chat.graph.nodes import generate as node

    retrieved = RETRIEVED + [
        {"chunk_id": "exp-majara#detail", "record_id": "exp-majara",
         "title": "Product Engineering intern", "text": "More."},
    ]
    monkeypatch.setattr(node, "structured", _fake(_answer(
        answer="ok", used_chunk_ids=["exp-majara#summary", "exp-majara#detail"],
    )))
    out = node.generate({"condensed": "q", "retrieved": retrieved})
    assert out["sources"] == [{"record_id": "exp-majara", "title": "Product Engineering intern"}]


def test_the_answer_uses_the_strong_model(monkeypatch):
    from chat.graph.nodes import generate as node

    seen = {}

    def fake(prompt, schema, *, fast=False):
        seen["fast"] = fast
        return _answer(answer="ok", used_chunk_ids=["exp-majara#summary"]), {}

    monkeypatch.setattr(node, "structured", fake)
    node.generate({"condensed": "q", "retrieved": RETRIEVED})
    assert seen["fast"] is False


def test_the_context_block_carries_every_retrieved_chunk_id(monkeypatch):
    from chat.graph.nodes import generate as node

    seen = {}

    def fake(prompt, schema, *, fast=False):
        seen["prompt"] = prompt
        return _answer(answer="ok", used_chunk_ids=["exp-majara#summary"]), {}

    monkeypatch.setattr(node, "structured", fake)
    node.generate({"condensed": "q", "retrieved": RETRIEVED})
    for c in RETRIEVED:
        assert c["chunk_id"] in seen["prompt"]
