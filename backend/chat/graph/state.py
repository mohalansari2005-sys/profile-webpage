from typing import Any, TypedDict


class ChatState(TypedDict, total=False):
    # inputs
    question: str
    history: list[dict[str, str]]
    ip_hash: str
    started_at: float

    # condense
    condensed: str

    # relevance
    in_scope: bool
    refusal_reason: str

    # retrieve
    retrieved: list[dict[str, Any]]

    # generate
    answer: str
    used_chunk_ids: list[str]
    sources: list[dict[str, str]]
    refused: bool

    # accounting
    usage: dict[str, int | None]
