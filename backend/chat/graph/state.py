from typing import Any, TypedDict


class ChatState(TypedDict, total=False):
    # inputs
    question: str
    history: list[dict[str, str]]
    ip_hash: str
    started_at: float

    # condense
    condensed: str
    # English text to embed for retrieval; falls back to `condensed`.
    search_query: str

    # relevance
    in_scope: bool
    refusal_reason: str
    # Set by any node whose OpenAI call failed outright. The turn is still
    # logged, but the view answers 503: the provider failed, not the question.
    unavailable: bool

    # retrieve
    retrieved: list[dict[str, Any]]

    # generate
    answer: str
    used_chunk_ids: list[str]
    sources: list[dict[str, str]]
    refused: bool

    # accounting
    usage: dict[str, int | None]
    model: str
