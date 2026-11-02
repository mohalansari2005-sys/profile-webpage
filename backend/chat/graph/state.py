from typing import Any, TypedDict


def is_outage(state: "ChatState") -> bool:
    """Whether a turn ended because OpenAI failed rather than on its merits:
    a call failed outright, or condense did and the turn then refused -- an
    unresolved follow-up or untranslated Arabic question is refused for a
    reason the visitor did not cause. The view answers these with a 503 and
    the log row says so."""
    return bool(state.get("unavailable") or (state.get("degraded") and state.get("refused")))


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
    # condense's call failed and the raw question went on. An answer still
    # stands; a refusal may be the missing rewrite's fault (see is_outage).
    degraded: bool

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
