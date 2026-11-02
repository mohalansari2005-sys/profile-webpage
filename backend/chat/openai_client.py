import contextvars
import logging
import math
import time
from contextlib import contextmanager

from django.conf import settings
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    ContentFilterFinishReasonError,
    InternalServerError,
    LengthFinishReasonError,
    OpenAI,
    OpenAIError,
    Timeout,
)
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Named openai_client, not openai, so it can never shadow the SDK it imports.
# SDK defaults (600s timeout, retries that sleep out a 429's Retry-After) suit
# ingest_content at deploy time. A visitor's turn runs under turn_budget below.
_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# The deadline of the turn in progress, set by the view. A turn is up to four
# sequential calls, and the browser gives up at 30s (frontend/lib/chat-api.ts):
# a fixed per-call timeout either outlasts that -- the visitor sees "couldn't
# reach" instead of the 503's "try again", and gunicorn kills the worker at
# 120s with no log row -- or is too short for a slow but healthy answer. Each
# call gets what is left of one budget instead.
_deadline: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "openai_deadline", default=None)

# The least budget worth starting a call with. Below it the call would time out
# after OpenAI had started -- and billed -- the work, for nothing.
MIN_SECONDS_FAST = 2.0
MIN_SECONDS_GENERATE = 6.0

# Output caps (max_completion_tokens). Without one a call may write up to the
# model's own maximum -- 32k tokens on gpt-4.1-mini -- from a prompt the visitor
# helped write, and CHAT_DAILY_CAP counts requests, not tokens. A call that
# reaches its cap raises LengthFinishReasonError: no usable response, flagged
# `truncated` with its billed tokens, so generate and relevance log the refusal
# as "output cap reached" (condense falls back to the raw question).
# The classifiers return a verdict, or condense's rewrite of a question of at
# most 1000 characters plus its English version.
MAX_TOKENS_FAST = 1000
# A long, detailed Arabic answer (Arabic takes roughly twice the tokens of the
# same English). The turn budget usually ends a call this long first; the cap
# is what bounds the bill for one the client gave up on.
MAX_TOKENS_GENERATE = 2500


@contextmanager
def turn_budget(seconds: float):
    token = _deadline.set(time.monotonic() + seconds)
    try:
        yield
    finally:
        _deadline.reset(token)


class _OutOfTime(Exception):
    """Too little of the turn's budget is left to start this call."""


def _call(model: str, min_seconds: float, send):
    """Runs send(client) within the turn's budget. Connect and read time both
    come out of what is left, so the budget is a deadline, not a per-call
    allowance. No SDK retries -- they sleep out a 429's Retry-After -- but one
    of our own for a dropped connection or a 5xx, the blips the SDK used to
    absorb, when the budget still allows it. Outside a turn (ingest, a shell)
    it is the plain client and the SDK's defaults."""
    deadline = _deadline.get()
    if deadline is None:
        return send(_client)
    for attempt in (1, 2):
        remaining = deadline - time.monotonic()
        if remaining < min_seconds:
            logger.error("OpenAI call skipped: model=%s, %.1fs of the turn budget left",
                         model, remaining)
            raise _OutOfTime
        connect = min(3.0, remaining / 4)
        client = _client.with_options(
            timeout=Timeout(remaining - connect, connect=connect), max_retries=0)
        try:
            return send(client)
        except (APIConnectionError, InternalServerError) as exc:
            # A timeout has already spent the budget; anything else, once.
            if attempt == 2 or isinstance(exc, APITimeoutError):
                raise
            logger.warning("OpenAI call retried: model=%s (%s)", model, type(exc).__name__)

# Set the first time OPENAI_FAST_MODEL comes back model_not_found. OpenAI retires
# models on a schedule -- gpt-4.1-nano was shut down on 2026-10-23 -- and
# backend/.env can pin a retired name, so a new default alone cannot be relied
# on. With nowhere to send the gate's call, it failed closed and refused every
# visitor; falling back to OPENAI_MODEL keeps it answering at a higher price
# until the env is fixed. Per process, so each gunicorn worker pays one failed
# call. Keyed on the error code, not the 404: OpenAI also answers 403 with it
# when a project cannot use a model, and an unrelated 404 must not flip this.
_fast_model_gone = False

# Codes for a request the API judged bad because of what the visitor sent: it
# fails the same way on every retry, so it is a refusal ("request rejected"),
# not an outage. Matched by code, not by 400: a 400 can also be configuration
# (a parameter the model does not take), and calling that "not an outage"
# would hide the next broken deploy behind refusals again.
# Not context_length_exceeded: visitor input is capped by the serializer, so an
# oversized prompt is the retrieved context's size -- the server's doing.
_REJECTED_CODES = {"invalid_prompt"}


def fast_model() -> str:
    """The model the classifier calls actually run on right now."""
    return settings.OPENAI_MODEL if _fast_model_gone else settings.OPENAI_FAST_MODEL


def _log_api_error(model: str, exc: APIError) -> None:
    # Status and error code say what went wrong (model_not_found,
    # insufficient_quota, invalid_api_key) without the message, which can echo
    # a masked fragment of the key.
    logger.error("OpenAI call failed: model=%s status=%s code=%s (%s)", model,
                 getattr(exc, "status_code", None), exc.code, type(exc).__name__)


def normalize(vec: list[float]) -> list[float]:
    """OpenAI returns unit vectors, and re-normalizes when `dimensions` shortens
    them. This is belt and braces: pgvector's cosine distance assumes unit
    length, and that assumption should not rest on a provider's guarantee."""
    norm = math.sqrt(sum(x * x for x in vec))
    return vec if norm == 0 else [x / norm for x in vec]


def _embed(client, texts: list[str]) -> list[list[float]]:
    """One call shape for both sides. Gemini needed a task_type asymmetry
    between documents and queries; OpenAI has no such parameter, so the two
    wrappers below differ only in arity."""
    resp = client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,
        input=texts,
        dimensions=settings.EMBED_DIMENSIONS,
    )
    return [normalize(d.embedding) for d in resp.data]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(_client, texts)


def embed_query(text: str) -> list[float] | None:
    """None means the API call itself failed (e.g. quota exhausted) -- the
    caller, retrieve(), finds nothing and flags the turn as an outage."""
    try:
        return _call(settings.OPENAI_EMBED_MODEL, MIN_SECONDS_FAST,
                     lambda client: _embed(client, [text]))[0]
    except APIError as exc:
        _log_api_error(settings.OPENAI_EMBED_MODEL, exc)
        return None
    except _OutOfTime:
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
    (condense, relevance), or OPENAI_MODEL once the fast one is not found.

    A failed API call (quota exhausted, rate limited, a 5xx that a retry did not
    clear, the turn's budget spent, a retired model with nowhere to fall back,
    an unexpected SDK error or a response that fails the schema) returns
    parsed=None with usage["api_error"] -- every caller already fails
    closed on parsed=None, and the flag is what stops a refusal log from
    calling an outage an "unparseable response".
    """
    global _fast_model_gone
    model = fast_model() if fast else settings.OPENAI_MODEL

    def send(client):
        return client.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
            max_completion_tokens=MAX_TOKENS_FAST if fast else MAX_TOKENS_GENERATE,
            # The classifiers are decisions, not prose. At the default
            # temperature the gate samples its verdict: the same question
            # measured 2/5 in_scope across five calls, so a visitor could be
            # refused and then answered on a retry. generate keeps the default
            # -- there the temperature shapes wording, and grounding is
            # enforced in Python regardless.
            **({"temperature": 0} if fast else {}),
        )

    try:
        resp = _call(model, MIN_SECONDS_FAST if fast else MIN_SECONDS_GENERATE, send)
    except _OutOfTime:
        return None, {"prompt_tokens": None, "completion_tokens": None, "api_error": True}
    except APIError as exc:
        _log_api_error(model, exc)
        if exc.code == "model_not_found" and model != settings.OPENAI_MODEL:
            logger.error("OPENAI_FAST_MODEL %s is gone; classifier calls now use "
                         "OPENAI_MODEL %s. Update backend/.env.", model, settings.OPENAI_MODEL)
            _fast_model_gone = True
            return structured(prompt, schema, fast=fast)
        if exc.code in _REJECTED_CODES:
            return None, {"prompt_tokens": None, "completion_tokens": None, "rejected": True}
        return None, {"prompt_tokens": None, "completion_tokens": None, "api_error": True}
    except (LengthFinishReasonError, ContentFilterFinishReasonError) as exc:
        # Neither subclasses APIError, so an `except APIError` alone lets these
        # escape as a 500. They mean the model produced nothing usable -- a bad
        # response, not an outage -- so they get no api_error flag. A length
        # cut-off is billed in full, and carries the completion: its counts
        # are logged, or the costliest calls would be the ones missing.
        usage = getattr(getattr(exc, "completion", None), "usage", None)
        counts = {"prompt_tokens": getattr(usage, "prompt_tokens", None),
                  "completion_tokens": getattr(usage, "completion_tokens", None)}
        if isinstance(exc, LengthFinishReasonError):
            # Its own refusal reason. Logged as "unparseable response", a cut-off
            # answer could be told from a real parse failure only by its token
            # count -- and how often the cap is hit is what to resize it by.
            counts["truncated"] = True
        return None, counts
    except (OpenAIError, ValidationError):
        # Any other SDK error, or pydantic's ValidationError when parse checks
        # the content against the schema -- no OpenAIError at all, and it
        # escaped as a 500 with no log row. Either is systematic: an SDK
        # upgrade or a schema the model cannot meet fails the same way for
        # every visitor. Called a bad response, each would have been refused
        # as off-topic or unanswerable, which is how a retired model went
        # unnoticed for ten days. So it is an outage: a 503, logged with its
        # traceback.
        logger.exception("OpenAI call failed unexpectedly: model=%s", model)
        return None, {"prompt_tokens": None, "completion_tokens": None, "api_error": True}

    usage = getattr(resp, "usage", None)
    counts = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }
    # parsed is None when the model refused rather than answering. The call
    # succeeded, so the token counts are real and worth logging, and there is
    # no api_error: this was a bad response, not an outage.
    return getattr(resp.choices[0].message, "parsed", None), counts


def failure_reason(usage: dict, otherwise: str) -> str:
    """The refusal_reason for a call that produced nothing usable: an outage, a
    request OpenAI rejected for what the visitor sent, a response cut off at
    its output cap, or the caller's own."""
    if usage.get("api_error"):
        return "generation unavailable"
    if usage.get("rejected"):
        return "request rejected"
    if usage.get("truncated"):
        return "output cap reached"
    return otherwise
