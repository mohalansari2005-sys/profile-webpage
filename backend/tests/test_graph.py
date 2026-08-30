import pytest


@pytest.fixture
def stub_nodes(monkeypatch):
    """Replace every model call so the graph is exercised, not the API."""
    from chat.graph.nodes import condense, generate, relevance, retrieve

    def no_condense(*a, **k):
        raise AssertionError("condense should short-circuit in these tests")

    monkeypatch.setattr(condense, "structured", no_condense)
    monkeypatch.setattr(retrieve, "embed_query", lambda q: [0.0] * 1536)
    return {"condense": condense, "generate": generate,
            "relevance": relevance, "retrieve": retrieve}


def test_in_scope_question_reaches_generate_and_logs(db, stub_nodes, monkeypatch):
    from chat.graph.build import build_graph
    from chat.graph.nodes.generate import Answer
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog, ContentChunk

    ContentChunk.objects.create(
        chunk_id="exp-a#summary", record_id="exp-a", kind="experience",
        title="Engineer", text="Built services.", content_hash="h",
        embedding=[0.0] * 1536,
    )
    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(in_scope=True, reason="ok"), {}))
    monkeypatch.setattr(stub_nodes["generate"], "structured", lambda *a, **k: (
        Answer(answer="He built services.", used_chunk_ids=["exp-a#summary"],
               sufficient=True), {"prompt_tokens": 1, "completion_tokens": 2}))

    out = build_graph().invoke({
        "question": "what did he build", "history": [], "ip_hash": "h" * 64,
        "started_at": 0.0,
    })

    assert out["refused"] is False
    assert out["sources"] == [{"record_id": "exp-a", "title": "Engineer"}]
    row = ChatLog.objects.get()
    assert row.refused is False
    assert row.retrieved_chunk_ids == ["exp-a#summary"]
    assert row.used_chunk_ids == ["exp-a#summary"]
    assert row.prompt_tokens == 1


def test_out_of_scope_question_skips_retrieval_but_still_logs(db, stub_nodes, monkeypatch):
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(in_scope=False, reason="weather"), {}))

    def no_embed(q):
        raise AssertionError("out-of-scope questions must not embed or retrieve")

    monkeypatch.setattr(stub_nodes["retrieve"], "embed_query", no_embed)

    out = build_graph().invoke({
        "question": "weather in Riyadh", "history": [], "ip_hash": "h" * 64,
        "started_at": 0.0,
    })

    assert out["refused"] is True
    assert out["sources"] == []
    row = ChatLog.objects.get()
    assert row.refused is True
    assert row.refusal_reason == "weather"
    assert row.retrieved_chunk_ids == []


def test_the_log_row_never_holds_a_raw_ip(db, stub_nodes, monkeypatch):
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog, hash_ip

    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(in_scope=False, reason="nope"), {}))
    build_graph().invoke({"question": "q", "history": [],
                          "ip_hash": hash_ip("203.0.113.9"), "started_at": 0.0})
    assert "203.0.113.9" not in ChatLog.objects.get().ip_hash


def test_a_scope_refusal_logs_the_fast_model_not_the_strong_one(db, stub_nodes, monkeypatch, settings):
    """The gate refuses without ever reaching generate, so attributing that row
    to the answer model would misreport the refusal analytics."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    settings.GEMINI_MODEL = "strong-model"
    settings.GEMINI_FAST_MODEL = "fast-model"
    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(in_scope=False, reason="weather"), {}))

    build_graph().invoke({"question": "weather", "history": [],
                          "ip_hash": "h" * 64, "started_at": 0.0})
    assert ChatLog.objects.get().model == "fast-model"
