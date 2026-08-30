import math

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel

_client = genai.Client(api_key=settings.GEMINI_API_KEY)


def normalize(vec: list[float]) -> list[float]:
    """Matryoshka-truncated vectors are no longer unit length, and pgvector's
    cosine distance assumes they are."""
    norm = math.sqrt(sum(x * x for x in vec))
    return vec if norm == 0 else [x / norm for x in vec]


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    resp = _client.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=settings.EMBED_DIMENSIONS,
        ),
    )
    return [normalize(list(e.values)) for e in resp.embeddings]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(texts, "RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    return _embed([text], "RETRIEVAL_QUERY")[0]


def structured(prompt: str, schema: type[BaseModel], *, fast: bool = False):
    """Returns (parsed, usage). response_schema guarantees the shape, so no
    caller ever parses a refusal out of prose.

    `fast=True` selects GEMINI_FAST_MODEL for the cheap classifier calls
    (condense, relevance). No thinking_budget is ever sent: the fast models
    reject it with a 400, and on the strong model it saved ~1s of 11.
    """
    resp = _client.models.generate_content(
        model=settings.GEMINI_FAST_MODEL if fast else settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    usage = getattr(resp, "usage_metadata", None)
    return resp.parsed, {
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "completion_tokens": getattr(usage, "candidates_token_count", None),
    }
