import math

import httpx
import pytest
from openai import (
    APITimeoutError,
    OpenAIError,
    BadRequestError,
    ConflictError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, ValidationError


class Shape(BaseModel):
    """A real BaseModel: `parse` is handed the class itself as response_format,
    so the bare `dict` the old Gemini tests passed no longer stands in."""
    ok: bool
    why: str


SHAPE = Shape(ok=True, why="because")


def _fake_client(embed_hook=None, parse_hook=None, parsed=SHAPE, raises=None):
    class FakeEmbeddings:
        def create(self, *, model, input, dimensions):
            if embed_hook:
                embed_hook(model, input, dimensions)
            return type("R", (), {"data": [
                type("D", (), {"embedding": [3.0, 4.0]})() for _ in input]})()

    class FakeCompletions:
        def parse(self, *, model, messages, response_format, **kwargs):
            if parse_hook:
                parse_hook(model, messages, response_format, kwargs)
            if raises:
                raise raises
            message = type("M", (), {"parsed": parsed})()
            return type("R", (), {
                "choices": [type("C", (), {"message": message})()],
                "usage": type("U", (), {"prompt_tokens": 11, "completion_tokens": 7})(),
            })()

    return type("Client", (), {
        "embeddings": FakeEmbeddings(),
        "chat": type("Chat", (), {"completions": FakeCompletions()})(),
    })()


def _rate_limit_error():
    return RateLimitError(
        "rate limit reached",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")),
        body=None,
    )


def _status_error(cls, status, code, message="error"):
    return cls(message, response=httpx.Response(
        status, request=httpx.Request("POST", "https://api.openai.com")), body={"code": code})


def _missing(*models, cls=NotFoundError, status=404):
    """A parse_hook under which the named models are gone; it records every
    model and temperature the client was asked for."""
    seen = []

    def hook(model, messages, fmt, kwargs):
        seen.append((model, kwargs.get("temperature")))
        if model in models:
            raise _status_error(cls, status, "model_not_found",
                                f"The model `{model}` does not exist or you do not have access to it.")
    return hook, seen


def test_normalize_returns_a_unit_vector():
    from chat.openai_client import normalize

    out = normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0, rel_tol=1e-9)
    assert math.isclose(out[0], 0.6, rel_tol=1e-9)


def test_normalize_leaves_a_zero_vector_alone():
    from chat.openai_client import normalize

    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_embed_documents_requests_the_column_dimension(monkeypatch, settings):
    """Asking for a width the ContentChunk vector column does not have is the
    one embedding mistake that fails at write time, not read time."""
    from chat import openai_client

    settings.OPENAI_EMBED_MODEL = "embed-model"
    seen = {}
    monkeypatch.setattr(openai_client, "_client", _fake_client(
        embed_hook=lambda m, i, d: seen.update(model=m, dims=d, n=len(i))))

    out = openai_client.embed_documents(["a", "b"])
    assert seen == {"model": "embed-model", "dims": 1536, "n": 2}
    assert len(out) == 2
    assert math.isclose(math.sqrt(sum(x * x for x in out[0])), 1.0, rel_tol=1e-9)


def test_embed_query_sends_one_text_and_returns_one_vector(monkeypatch):
    from chat import openai_client

    seen = {}
    monkeypatch.setattr(openai_client, "_client", _fake_client(
        embed_hook=lambda m, i, d: seen.update(inputs=i)))

    out = openai_client.embed_query("who is he")
    assert seen["inputs"] == ["who is he"]
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0, rel_tol=1e-9)


def test_embed_query_fails_closed_on_an_api_error(monkeypatch):
    from chat import openai_client

    class Failing:
        def create(self, *, model, input, dimensions):
            raise _rate_limit_error()

    monkeypatch.setattr(openai_client, "_client",
                        type("C", (), {"embeddings": Failing()})())
    assert openai_client.embed_query("who is he") is None


def test_structured_uses_the_strong_model_by_default(monkeypatch, settings):
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "fast-model"
    seen = {}
    monkeypatch.setattr(openai_client, "_client",
                        _fake_client(parse_hook=lambda m, msg, fmt, kw: seen.update(model=m)))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert seen["model"] == "strong-model"
    assert parsed == SHAPE
    assert usage == {"prompt_tokens": 11, "completion_tokens": 7}


def test_structured_uses_the_fast_model_when_asked(monkeypatch, settings):
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "fast-model"
    seen = {}
    monkeypatch.setattr(openai_client, "_client",
                        _fake_client(parse_hook=lambda m, msg, fmt, kw: seen.update(model=m)))

    openai_client.structured("prompt", Shape, fast=True)
    assert seen["model"] == "fast-model"


def test_structured_hands_the_schema_class_to_the_sdk(monkeypatch):
    """`parse` derives and enforces the JSON schema server-side. Passing the
    class, not a hand-built dict, is what keeps that guarantee."""
    from chat import openai_client

    seen = {}
    monkeypatch.setattr(openai_client, "_client",
                        _fake_client(parse_hook=lambda m, msg, fmt, kw: seen.update(fmt=fmt)))

    openai_client.structured("prompt", Shape)
    assert seen["fmt"] is Shape


def test_structured_fails_closed_on_a_rate_limit_error(monkeypatch):
    """A 429 must not crash the request -- it should look like an unparseable
    response to callers, who already fail closed on that."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client",
                        _fake_client(raises=_rate_limit_error()))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage == {"prompt_tokens": None, "completion_tokens": None, "api_error": True}


def _truncated_completion():
    return ChatCompletion(id="x", choices=[], created=0, model="m",
                          object="chat.completion")


@pytest.mark.parametrize("error, flags", [
    pytest.param(ContentFilterFinishReasonError(), {}, id="content-filter"),
    pytest.param(LengthFinishReasonError(completion=_truncated_completion()),
                 {"truncated": True}, id="length-truncated"),
])
def test_finish_reason_errors_do_not_escape(monkeypatch, error, flags):
    """LengthFinishReasonError and ContentFilterFinishReasonError subclass
    OpenAIError, NOT APIError -- an `except APIError` alone lets them escape as
    a 500. They mean a bad response, not an outage, so no api_error flag."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(raises=error))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage == {"prompt_tokens": None, "completion_tokens": None, **flags}
    assert "api_error" not in usage


def _validation_error():
    try:
        Shape.model_validate_json("{}")
    except ValidationError as exc:
        return exc


@pytest.mark.parametrize("error", [
    pytest.param(_validation_error, id="pydantic-validation"),
    pytest.param(lambda: OpenAIError("unexpected"), id="other-openai-error"),
])
def test_an_unusable_response_is_refused_not_a_500(monkeypatch, caplog, error):
    """parse validates the content with pydantic, whose ValidationError is no
    OpenAIError at all, so it escaped every except here as a 500 with no
    ChatLog row. A bad response, not an outage -- and logged, with its
    traceback, so it is not a silent refusal either."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(raises=error()))
    with caplog.at_level("ERROR", logger="chat.openai_client"):
        parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage == {"prompt_tokens": None, "completion_tokens": None}
    assert caplog.records[-1].exc_info is not None


def test_every_call_caps_its_output(monkeypatch):
    """Without a cap a call may write up to the model's own maximum -- 32k
    tokens on gpt-4.1-mini -- from a visitor-written prompt, and
    CHAT_DAILY_CAP counts requests, not tokens."""
    from chat import openai_client

    seen = []
    monkeypatch.setattr(openai_client, "_client", _fake_client(
        parse_hook=lambda m, msg, fmt, kw: seen.append(kw.get("max_completion_tokens"))))
    openai_client.structured("prompt", Shape, fast=True)
    openai_client.structured("prompt", Shape)
    assert seen == [openai_client.MAX_TOKENS_FAST, openai_client.MAX_TOKENS_GENERATE]


def test_the_sdk_takes_the_output_cap():
    """The fakes would not notice the SDK renaming or dropping the parameter."""
    import inspect

    from chat import openai_client

    assert "max_completion_tokens" in inspect.signature(
        openai_client._client.chat.completions.parse).parameters


def test_a_capped_answer_still_reports_what_it_cost(monkeypatch):
    """Cut off at the cap, the call is billed in full. Logged as None, the
    most expensive calls were the ones missing from ChatLog."""
    from openai.types import CompletionUsage

    from chat import openai_client

    completion = ChatCompletion(
        id="x", choices=[], created=0, model="m", object="chat.completion",
        usage=CompletionUsage(prompt_tokens=900, completion_tokens=2500, total_tokens=3400))
    monkeypatch.setattr(openai_client, "_client", _fake_client(
        raises=LengthFinishReasonError(completion=completion)))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage == {"prompt_tokens": 900, "completion_tokens": 2500, "truncated": True}
    assert openai_client.failure_reason(usage, "unparseable response") == "output cap reached"


def test_a_refusal_is_not_reported_as_an_api_error(monkeypatch):
    """`parsed` is None when the model refused instead of answering. The call
    succeeded, so the token counts are real and api_error must be absent --
    that flag decides whether the refusal log says "generation unavailable"."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(parsed=None))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage == {"prompt_tokens": 11, "completion_tokens": 7}
    assert "api_error" not in usage


def test_merge_usage_adds_counts_from_calls_on_the_same_model():
    from chat.openai_client import merge_usage

    merged = merge_usage({"prompt_tokens": 30, "completion_tokens": 5},
                         {"prompt_tokens": 40, "completion_tokens": 9})
    assert merged == {"prompt_tokens": 70, "completion_tokens": 14}


def test_merge_usage_keeps_unreported_counts_as_none_not_zero():
    """A row of zeros reads as "the call happened and cost nothing", which is a
    different claim from "nobody reported what it cost"."""
    from chat.openai_client import merge_usage

    merged = merge_usage(None, {"prompt_tokens": None, "completion_tokens": None})
    assert merged == {"prompt_tokens": None, "completion_tokens": None}


def test_merge_usage_keeps_a_reported_count_when_another_call_reported_nothing():
    from chat.openai_client import merge_usage

    merged = merge_usage({"prompt_tokens": None, "completion_tokens": None},
                         {"prompt_tokens": 40, "completion_tokens": 9})
    assert merged == {"prompt_tokens": 40, "completion_tokens": 9}


def test_merge_usage_propagates_an_api_error_from_any_call():
    """condense failing upstream must not be erased by a gate call that worked;
    the flag is what keeps a refusal log honest about an outage."""
    from chat.openai_client import merge_usage

    merged = merge_usage({"prompt_tokens": None, "completion_tokens": None, "api_error": True},
                         {"prompt_tokens": 40, "completion_tokens": 9})
    assert merged["api_error"] is True


def test_the_classifiers_are_pinned_to_a_deterministic_temperature(monkeypatch):
    """The gate must not sample its verdict: measured against the live model, one
    borderline question came back in_scope on 2 of 5 identical calls, so the same
    visitor could be refused and then answered on a retry."""
    from chat import openai_client

    seen = {}
    monkeypatch.setattr(openai_client, "_client",
                        _fake_client(parse_hook=lambda m, msg, fmt, kw: seen.update(kw)))
    openai_client.structured("q", Shape, fast=True)
    assert seen["temperature"] == 0


def test_generate_keeps_the_default_temperature(monkeypatch):
    """Only the classifiers are pinned. generate writes prose, where sampling
    costs nothing -- grounding is enforced in Python, not by the temperature."""
    from chat import openai_client

    seen = {}
    monkeypatch.setattr(openai_client, "_client",
                        _fake_client(parse_hook=lambda m, msg, fmt, kw: seen.update(kw=kw)))
    openai_client.structured("q", Shape)
    assert "temperature" not in seen["kw"]


def test_a_retired_fast_model_falls_back_to_the_strong_model(monkeypatch, settings):
    """gpt-4.1-nano was shut down on 2026-10-23 while backend/.env could still
    name it. The gate must keep answering on OPENAI_MODEL -- at the classifier
    temperature -- and stop paying a failed call once it knows."""
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "retired-model"
    monkeypatch.setattr(openai_client, "_fast_model_gone", False)
    hook, seen = _missing("retired-model")
    monkeypatch.setattr(openai_client, "_client", _fake_client(parse_hook=hook))

    parsed, usage = openai_client.structured("prompt", Shape, fast=True)
    assert parsed == SHAPE
    assert "api_error" not in usage
    assert openai_client.fast_model() == "strong-model"

    openai_client.structured("prompt", Shape, fast=True)
    assert seen == [("retired-model", 0), ("strong-model", 0), ("strong-model", 0)]


def test_a_model_the_project_cannot_use_falls_back_too(monkeypatch, settings):
    """OpenAI answers 403, not 404, with the same model_not_found code when a
    key's project has no access to a model; the code is what decides."""
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "blocked-model"
    monkeypatch.setattr(openai_client, "_fast_model_gone", False)
    hook, _ = _missing("blocked-model", cls=PermissionDeniedError, status=403)
    monkeypatch.setattr(openai_client, "_client", _fake_client(parse_hook=hook))

    parsed, _ = openai_client.structured("prompt", Shape, fast=True)
    assert parsed == SHAPE


def test_an_unrelated_404_does_not_abandon_the_fast_model(monkeypatch, settings):
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "fast-model"
    monkeypatch.setattr(openai_client, "_fast_model_gone", False)
    monkeypatch.setattr(openai_client, "_client", _fake_client(
        raises=_status_error(NotFoundError, 404, None, "Not Found")))

    parsed, usage = openai_client.structured("prompt", Shape, fast=True)
    assert (parsed, usage["api_error"]) == (None, True)
    assert openai_client.fast_model() == "fast-model"


def test_a_missing_strong_model_is_an_outage_not_a_loop(monkeypatch, settings):
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "retired-model"
    monkeypatch.setattr(openai_client, "_fast_model_gone", False)
    hook, seen = _missing("retired-model", "strong-model")
    monkeypatch.setattr(openai_client, "_client", _fake_client(parse_hook=hook))

    parsed, usage = openai_client.structured("prompt", Shape, fast=True)
    assert parsed is None
    assert usage["api_error"] is True
    assert [m for m, _ in seen] == ["retired-model", "strong-model"]


def test_a_missing_generate_model_does_not_touch_the_fast_one(monkeypatch, settings):
    from chat import openai_client

    settings.OPENAI_MODEL = "strong-model"
    settings.OPENAI_FAST_MODEL = "fast-model"
    monkeypatch.setattr(openai_client, "_fast_model_gone", False)
    hook, _ = _missing("strong-model")
    monkeypatch.setattr(openai_client, "_client", _fake_client(parse_hook=hook))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert (parsed, usage["api_error"]) == (None, True)
    assert openai_client.fast_model() == "fast-model"


def test_a_rejected_prompt_is_not_an_outage(monkeypatch):
    """A flagged prompt fails the same way on every retry. Reported as an
    outage, the visitor would be told to try again, forever."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(
        raises=_status_error(BadRequestError, 400, "invalid_prompt")))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage.get("rejected") is True
    assert "api_error" not in usage


@pytest.mark.parametrize("error", [
    pytest.param(lambda: _status_error(BadRequestError, 400, "unsupported_parameter"),
                 id="config-400"),
    pytest.param(lambda: _status_error(ConflictError, 409, None), id="conflict-409"),
    # Visitor input is capped; an oversized prompt is the retrieved context.
    pytest.param(lambda: _status_error(BadRequestError, 400, "context_length_exceeded"),
                 id="context-length"),
])
def test_a_config_error_or_a_conflict_is_an_outage(monkeypatch, error):
    """A 400 can be configuration -- a parameter the model does not take --
    and the SDK retries a 409 as transient. Calling either "not an outage"
    would hide a broken deploy behind refusals again."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(raises=error()))
    parsed, usage = openai_client.structured("prompt", Shape)
    assert (parsed, usage.get("api_error")) == (None, True)


def test_an_api_error_is_logged_without_its_message(monkeypatch, caplog):
    """The status and code say what broke; the message can echo a masked
    fragment of the key, so it stays out of the logs."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(raises=_rate_limit_error()))
    with caplog.at_level("ERROR", logger="chat.openai_client"):
        openai_client.structured("prompt", Shape)
    assert "status=429" in caplog.text
    assert "rate limit reached" not in caplog.text


def _budgeted_client(seen, fail_first=None):
    """A fake whose with_options records what each attempt was allowed, and
    whose first call can raise."""
    base = _fake_client()
    calls = {"n": 0}
    real_parse = base.chat.completions.parse

    def parse(**kw):
        calls["n"] += 1
        if fail_first is not None and calls["n"] == 1:
            raise fail_first
        return real_parse(**kw)

    base.chat.completions.parse = parse

    def with_options(**kw):
        seen.append(kw)
        return base

    base.with_options = with_options
    return base


def _internal_error():
    return InternalServerError("upstream", response=httpx.Response(
        502, request=httpx.Request("POST", "https://api.openai.com")), body=None)


def test_inside_a_turn_each_call_gets_the_remaining_budget_and_no_sdk_retries(monkeypatch):
    """SDK retries sleep out a 429's Retry-After, and connect time on top of a
    full read timeout would overrun the browser's 30s."""
    from chat import openai_client

    seen = []
    monkeypatch.setattr(openai_client, "_client", _budgeted_client(seen))
    with openai_client.turn_budget(10):
        parsed, _ = openai_client.structured("prompt", Shape)
        openai_client.embed_query("q")

    assert parsed == SHAPE
    assert [kw["max_retries"] for kw in seen] == [0, 0]
    assert all(kw["timeout"].connect + kw["timeout"].read <= 10 for kw in seen)


def test_the_real_client_accepts_the_budgeted_options():
    """The fakes above would not notice the SDK rejecting the timeout type."""
    from chat import openai_client

    with openai_client.turn_budget(10):
        client = openai_client._call("m", 2.0, lambda c: c)
    assert client.max_retries == 0
    assert client.timeout.connect + client.timeout.read <= 10


def test_one_blip_is_retried_within_the_budget(monkeypatch):
    from chat import openai_client

    seen = []
    monkeypatch.setattr(openai_client, "_client", _budgeted_client(seen, _internal_error()))
    with openai_client.turn_budget(10):
        parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed == SHAPE and "api_error" not in usage
    assert len(seen) == 2


def test_a_timeout_is_not_retried(monkeypatch):
    """It has already spent the budget a retry would need."""
    from chat import openai_client

    seen = []
    timeout = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
    monkeypatch.setattr(openai_client, "_client", _budgeted_client(seen, timeout))
    with openai_client.turn_budget(10):
        parsed, usage = openai_client.structured("prompt", Shape)
    assert (parsed, usage["api_error"]) == (None, True)
    assert len(seen) == 1


def test_generate_is_not_started_without_the_time_to_finish(monkeypatch):
    """OpenAI bills a generation the client gave up on. With 4s left the
    classifier may run, the answer may not."""
    from chat import openai_client

    seen = []
    monkeypatch.setattr(openai_client, "_client", _budgeted_client(seen))
    with openai_client.turn_budget(4):
        fast, _ = openai_client.structured("prompt", Shape, fast=True)
        answer, usage = openai_client.structured("prompt", Shape)
    assert fast == SHAPE
    assert (answer, usage["api_error"]) == (None, True)
    assert len(seen) == 1


def test_outside_a_turn_the_sdk_defaults_apply(monkeypatch):
    """ingest_content runs at deploy time with no visitor waiting: it keeps the
    SDK's patience rather than a turn's budget."""
    from chat import openai_client

    client = _fake_client()
    client.with_options = lambda **kw: (_ for _ in ()).throw(AssertionError("not in a turn"))
    monkeypatch.setattr(openai_client, "_client", client)
    assert len(openai_client.embed_documents(["a"])) == 1
    assert openai_client.structured("prompt", Shape)[0] == SHAPE
