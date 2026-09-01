import math

import httpx
import pytest
from openai import (
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion
from pydantic import BaseModel


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


@pytest.mark.parametrize("error", [
    pytest.param(ContentFilterFinishReasonError(), id="content-filter"),
    pytest.param(LengthFinishReasonError(completion=_truncated_completion()),
                 id="length-truncated"),
])
def test_finish_reason_errors_do_not_escape(monkeypatch, error):
    """LengthFinishReasonError and ContentFilterFinishReasonError subclass
    OpenAIError, NOT APIError -- an `except APIError` alone lets them escape as
    a 500. They mean a bad response, not an outage, so no api_error flag."""
    from chat import openai_client

    monkeypatch.setattr(openai_client, "_client", _fake_client(raises=error))

    parsed, usage = openai_client.structured("prompt", Shape)
    assert parsed is None
    assert usage == {"prompt_tokens": None, "completion_tokens": None}
    assert "api_error" not in usage


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
