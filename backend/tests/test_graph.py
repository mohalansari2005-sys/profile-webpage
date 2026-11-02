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
                        lambda *a, **k: (Relevance(subject="mohammed", reason="ok"), {}))
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
                        lambda *a, **k: (Relevance(subject="general", reason="weather"), {}))

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
    assert row.refusal_reason == "general: weather"
    assert row.retrieved_chunk_ids == []
    # Declining a question is not an outage.
    assert row.unavailable is False


@pytest.mark.parametrize("synthetic", [True, False])
def test_the_view_s_synthetic_flag_reaches_the_log_row(db, stub_nodes, monkeypatch, synthetic):
    """LangGraph drops input keys the state does not declare, so this checks
    the flag survives the trip from the view to the row."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(subject="general", reason="weather"), {}))
    build_graph().invoke({"question": "weather in Riyadh", "history": [], "ip_hash": "h" * 64,
                          "started_at": 0.0, "synthetic": synthetic})
    assert ChatLog.objects.get().synthetic is synthetic


def test_the_log_row_never_holds_a_raw_ip(db, stub_nodes, monkeypatch):
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog, hash_ip

    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(subject="general", reason="nope"), {}))
    build_graph().invoke({"question": "q", "history": [],
                          "ip_hash": hash_ip("203.0.113.9"), "started_at": 0.0})
    assert "203.0.113.9" not in ChatLog.objects.get().ip_hash


def test_a_scope_refusal_logs_the_fast_model_not_the_strong_one(db, stub_nodes, monkeypatch, settings):
    """The gate refuses without ever reaching generate, so attributing that row
    to the answer model would misreport the refusal analytics."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "fast-model"
    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (Relevance(subject="general", reason="weather"), {}))

    build_graph().invoke({"question": "weather", "history": [],
                          "ip_hash": "h" * 64, "started_at": 0.0})
    assert ChatLog.objects.get().model == "fast-model"


def test_a_scope_refusal_logs_the_tokens_the_gate_actually_spent(db, stub_nodes, monkeypatch):
    """A refused turn is not a free turn -- the gate call is billable. Logging
    None there let the cheapest-looking path hide real spend."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    monkeypatch.setattr(stub_nodes["relevance"], "structured", lambda *a, **k: (
        Relevance(subject="general", reason="weather"),
        {"prompt_tokens": 40, "completion_tokens": 9}))

    build_graph().invoke({"question": "weather", "history": [],
                          "ip_hash": "h" * 64, "started_at": 0.0})

    row = ChatLog.objects.get()
    assert (row.prompt_tokens, row.completion_tokens) == (40, 9)


def test_a_refused_follow_up_sums_condense_and_the_gate(db, stub_nodes, monkeypatch):
    """Both run on OPENAI_FAST_MODEL, so their tokens are the same currency and
    the row's model still describes every token counted in it."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.condense import Standalone
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    monkeypatch.setattr(stub_nodes["condense"], "structured", lambda *a, **k: (
        Standalone(standalone_question="what is the weather there"),
        {"prompt_tokens": 30, "completion_tokens": 5}))
    monkeypatch.setattr(stub_nodes["relevance"], "structured", lambda *a, **k: (
        Relevance(subject="general", reason="weather"),
        {"prompt_tokens": 40, "completion_tokens": 9}))

    build_graph().invoke({
        "question": "and there?", "ip_hash": "h" * 64, "started_at": 0.0,
        "history": [{"role": "user", "content": "tell me about Riyadh"},
                    {"role": "assistant", "content": "He worked there."}],
    })

    row = ChatLog.objects.get()
    assert (row.prompt_tokens, row.completion_tokens) == (70, 14)


def test_an_answered_turn_reports_only_the_answer_model_s_tokens(db, stub_nodes, monkeypatch):
    """The fast calls are billed at a different rate, so adding them to the row
    would misprice it: the row names one model and must count only that one."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.generate import Answer
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog, ContentChunk

    ContentChunk.objects.create(
        chunk_id="exp-a#summary", record_id="exp-a", kind="experience",
        title="Engineer", text="Built services.", content_hash="h",
        embedding=[0.0] * 1536,
    )
    monkeypatch.setattr(stub_nodes["relevance"], "structured", lambda *a, **k: (
        Relevance(subject="mohammed", reason="ok"),
        {"prompt_tokens": 40, "completion_tokens": 9}))
    monkeypatch.setattr(stub_nodes["generate"], "structured", lambda *a, **k: (
        Answer(answer="He built services.", used_chunk_ids=["exp-a#summary"],
               sufficient=True),
        {"prompt_tokens": 500, "completion_tokens": 80}))

    build_graph().invoke({"question": "what did he build", "history": [],
                          "ip_hash": "h" * 64, "started_at": 0.0})

    row = ChatLog.objects.get()
    assert (row.prompt_tokens, row.completion_tokens) == (500, 80)


def test_an_embedding_outage_is_logged_and_flagged_not_called_empty(db, stub_nodes, monkeypatch, settings):
    """embed_query returns None when the API call fails. Treated as an empty
    search, that told the visitor "I don't have that" during an outage."""
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    settings.OPENAI_FAST_MODEL = "fast-model"
    monkeypatch.setattr(stub_nodes["relevance"], "structured", lambda *a, **k: (
        Relevance(subject="mohammed", reason="ok"), {"prompt_tokens": 40, "completion_tokens": 9}))
    monkeypatch.setattr(stub_nodes["retrieve"], "embed_query", lambda q: None)

    def no_generate(*a, **k):
        raise AssertionError("generate must not call the model with nothing retrieved")

    monkeypatch.setattr(stub_nodes["generate"], "structured", no_generate)

    out = build_graph().invoke({"question": "what did he build", "history": [],
                                "ip_hash": "h" * 64, "started_at": 0.0})
    assert out["unavailable"] is True
    row = ChatLog.objects.get()
    # Says what failed, and keeps the gate's spend on the gate's model.
    assert (row.refusal_reason, row.model) == ("retrieval unavailable", "fast-model")
    assert (row.prompt_tokens, row.completion_tokens) == (40, 9)


def test_a_gate_outage_is_logged_and_flagged(db, stub_nodes, monkeypatch):
    from chat.graph.build import build_graph
    from chat.models import ChatLog

    monkeypatch.setattr(stub_nodes["relevance"], "structured",
                        lambda *a, **k: (None, {"prompt_tokens": None,
                                                "completion_tokens": None, "api_error": True}))

    out = build_graph().invoke({"question": "What is Keyraa?", "history": [],
                                "ip_hash": "h" * 64, "started_at": 0.0})
    assert out["unavailable"] is True
    row = ChatLog.objects.get()
    assert row.refusal_reason == "generation unavailable"
    # The flag the dashboard counts outages by, not the wording above.
    assert row.unavailable is True


def test_a_response_that_fails_the_schema_is_an_outage_not_a_refusal(db, stub_nodes, monkeypatch):
    """Through the real structured(): refused as off-topic, a schema the model
    cannot meet would turn every visitor away and look like their fault."""
    from chat import openai_client
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance
    from chat.models import ChatLog

    class Completions:
        def parse(self, **kwargs):
            return Relevance.model_validate_json("{}")  # raises ValidationError

    monkeypatch.setattr(openai_client, "_client", type("C", (), {
        "chat": type("Chat", (), {"completions": Completions()})()})())
    out = build_graph().invoke({"question": "What is Keyraa?", "history": [],
                                "ip_hash": "h" * 64, "started_at": 0.0})
    assert out["unavailable"] is True
    assert ChatLog.objects.get().refusal_reason == "generation unavailable"


def _condense_fails(stub_nodes, monkeypatch):
    monkeypatch.setattr(stub_nodes["condense"], "structured", lambda *a, **k: (
        None, {"prompt_tokens": None, "completion_tokens": None, "api_error": True}))


FOLLOW_UP = {"ip_hash": "h" * 64, "started_at": 0.0,
             "history": [{"role": "user", "content": "tell me about Majara"},
                         {"role": "assistant", "content": "He works there."}]}


def test_a_condense_outage_ends_the_turn_without_a_gate_call(db, stub_nodes, monkeypatch):
    """Unresolved, "what did he build there?" could come back a grounded answer
    about the wrong employer. The visitor gets the 503 instead, and the gate is
    not paid for a call that would most likely fail the same way."""
    from chat.graph.build import build_graph
    from chat.models import ChatLog

    _condense_fails(stub_nodes, monkeypatch)

    def no_gate(*a, **k):
        raise AssertionError("the gate must not be called after condense failed")

    monkeypatch.setattr(stub_nodes["relevance"], "structured", no_gate)
    out = build_graph().invoke({"question": "what did he build there?", **FOLLOW_UP})
    assert (out["unavailable"], out["in_scope"]) == (True, False)
    assert ChatLog.objects.get().refusal_reason == "condense unavailable"


def test_the_turn_budget_reaches_the_nodes(db, stub_nodes, monkeypatch):
    """The deadline travels in a ContextVar. If LangGraph stopped carrying it
    into nodes, every call would silently fall back to the SDK's 600s."""
    from chat import openai_client
    from chat.graph.build import build_graph
    from chat.graph.nodes.relevance import Relevance

    seen = {}

    def gate(*a, **k):
        seen["deadline"] = openai_client._deadline.get()
        return Relevance(subject="general", reason="mock"), {}

    monkeypatch.setattr(stub_nodes["relevance"], "structured", gate)
    with openai_client.turn_budget(10):
        build_graph().invoke({"question": "weather", "history": [],
                              "ip_hash": "h" * 64, "started_at": 0.0})
    assert seen["deadline"] is not None


def _answer_with_a_failing_log_write(stub_nodes, monkeypatch, error):
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
                        lambda *a, **k: (Relevance(subject="mohammed", reason="ok"), {}))
    monkeypatch.setattr(stub_nodes["generate"], "structured", lambda *a, **k: (
        Answer(answer="He built services.", used_chunk_ids=["exp-a#summary"],
               sufficient=True), {}))

    def broken(**kwargs):
        raise error

    monkeypatch.setattr(ChatLog.objects, "create", broken)
    return build_graph().invoke({"question": "what did he build", "history": [],
                                 "ip_hash": "h" * 64, "started_at": 0.0})


@pytest.mark.parametrize("error", [
    pytest.param(("OperationalError", "could not connect to server"), id="dropped-connection"),
    pytest.param(("InterfaceError", "connection already closed"), id="closed-connection"),
])
def test_a_failed_log_write_still_returns_the_answer(db, stub_nodes, monkeypatch, caplog, error):
    """The answer is generated -- and billed -- before log runs. A failed write
    (a full disk, a dropped connection) turned it into a 500 with no row."""
    from django import db as django_db

    name, message = error
    with caplog.at_level("ERROR", logger="chat.graph.nodes.log"):
        out = _answer_with_a_failing_log_write(stub_nodes, monkeypatch,
                                               getattr(django_db, name)(message))
    assert (out["refused"], out["answer"]) == (False, "He built services.")
    assert "ChatLog write failed" in caplog.text


@pytest.mark.parametrize("error", [
    pytest.param(("ProgrammingError", 'column "model" does not exist'), id="schema-drift"),
    pytest.param(("ProgrammingError", "permission denied for table chat_chatlog"), id="revoked-grant"),
    pytest.param(("IntegrityError", 'null value in column "question"'), id="not-null"),
    pytest.param(("DataError", "value too long"), id="bad-value"),
])
def test_a_broken_chatlog_still_fails_loudly(db, stub_nodes, monkeypatch, error):
    """These fail every turn the same way. Answered with a 200 anyway, ChatLog
    -- the only record of spend -- stopped recording while the canary, which
    checks only the answer, stayed green."""
    from django import db as django_db

    name, message = error
    with pytest.raises(getattr(django_db, name)):
        _answer_with_a_failing_log_write(stub_nodes, monkeypatch, getattr(django_db, name)(message))
