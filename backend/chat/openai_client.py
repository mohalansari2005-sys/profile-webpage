import math

from django.conf import settings
from openai import (
    APIError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    OpenAI,
)
from pydantic import BaseModel

# Named openai_client, not openai, so it can never shadow the SDK it imports.
_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def normalize(vec: list[float]) -> list[float]:
    """OpenAI returns unit vectors, and re-normalizes when `dimensions` shortens
    them. This is belt and braces: pgvector's cosine distance assumes unit
    length, and that assumption should not rest on a provider's guarantee."""
    norm = math.sqrt(sum(x * x for x in vec))
    return vec if norm == 0 else [x / norm for x in vec]


def _embed(texts: list[str]) -> list[list[float]]:
    """One call shape for both sides. Gemini needed a task_type asymmetry
    between documents and queries; OpenAI has no such parameter, so the two
    wrappers below differ only in arity."""
    resp = _client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,
        input=texts,
        dimensions=settings.EMBED_DIMENSIONS,
    )
    return [normalize(d.embedding) for d in resp.data]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(texts)


def embed_query(text: str) -> list[float] | None:
    """None means the API call itself failed (e.g. quota exhausted) -- the
    caller, retrieve(), treats that the same as finding nothing."""
    try:
        return _embed([text])[0]
    except APIError:
        return None


def merge_usage(*usages: dict | None) -> dict:
    """Add token counts from several calls **on the same model**.

    Never merge across models: a ChatLog row names one model, and tokens billed
    at two different rates summed into one number cannot be priced. condense and
    relevance both run on OPENAI_FAST_MODEL, so they merge; generate does not.

    None means "not reported", not zero -- an api_error carries no counts, and a
    merged 0 would read as a call that happened and cost nothing.
    """
    merged: dict = {}
    for key in ("prompt_tokens", "completion_tokens"):
        counts = [u[key] for u in usages if u and u.get(key) is not None]
        merged[key] = sum(counts) if counts else None
    if any(u and u.get("api_error") for u in usages):
        merged["api_error"] = True
    return merged


def structured(prompt: str, schema: type[BaseModel], *, fast: bool = False):
    """Returns (parsed, usage). `parse` enforces the schema server-side, so no
    caller ever parses a refusal out of prose.

    `fast=True` selects OPENAI_FAST_MODEL for the cheap classifier calls
    (condense, relevance).

    A failed API call (quota exhausted, rate limited, transient 5xx) returns
    parsed=None with usage["api_error"] -- every caller already fails closed on
    parsed=None, and the flag is what stops a refusal log from calling an
    outage an "unparseable response".
    """
    try:
        resp = _client.chat.completions.parse(
            model=settings.OPENAI_FAST_MODEL if fast else settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
            # The classifiers are decisions, not prose. At the default
            # temperature the gate samples its verdict: the same question
            # measured 2/5 in_scope across five calls, so a visitor could be
            # refused and then answered on a retry. generate keeps the default
            # -- there the temperature shapes wording, and grounding is
            # enforced in Python regardless.
            **({"temperature": 0} if fast else {}),
        )
    except APIError:
        return None, {"prompt_tokens": None, "completion_tokens": None, "api_error": True}
    except (LengthFinishReasonError, ContentFilterFinishReasonError):
        # Neither subclasses APIError, so an `except APIError` alone lets these
        # escape as a 500. They mean the model produced nothing usable -- a bad
        # response, not an outage -- so they get no api_error flag. Token counts
        # are unreachable on these, unlike the parse failures below.
        return None, {"prompt_tokens": None, "completion_tokens": None}

    usage = getattr(resp, "usage", None)
    counts = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }
    # parsed is None when the model refused rather than answering. The call
    # succeeded, so the token counts are real and worth logging, and there is
    # no api_error: this was a bad response, not an outage.
    return getattr(resp.choices[0].message, "parsed", None), counts
