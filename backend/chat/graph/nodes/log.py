import time

from django.conf import settings

from chat.graph.state import ChatState
from chat.models import ChatLog


def log(state: ChatState) -> dict:
    """Terminal node on both paths -- refusals are the most interesting rows."""
    usage = state.get("usage") or {}
    started = state.get("started_at") or time.monotonic()

    ChatLog.objects.create(
        ip_hash=state.get("ip_hash", ""),
        question=state.get("question", ""),
        condensed_question=state.get("condensed", ""),
        answer=state.get("answer", ""),
        refused=bool(state.get("refused", not state.get("in_scope", False))),
        refusal_reason=(state.get("refusal_reason") or "")[:200],
        retrieved_chunk_ids=[c["chunk_id"] for c in state.get("retrieved") or []],
        used_chunk_ids=state.get("used_chunk_ids") or [],
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        latency_ms=int((time.monotonic() - started) * 1000),
        model=settings.GEMINI_MODEL,
    )
    return {}
