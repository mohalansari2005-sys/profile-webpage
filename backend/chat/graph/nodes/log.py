import logging
import time

from django.conf import settings
from django.db import InterfaceError, OperationalError

from chat.graph.state import ChatState
from chat.models import ChatLog

logger = logging.getLogger(__name__)


def log(state: ChatState) -> dict:
    """Terminal node on both paths -- refusals are the most interesting rows."""
    usage = state.get("usage") or {}
    started = state.get("started_at") or time.monotonic()

    try:
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
            # The model that actually decided this turn: the gate refuses on the
            # fast model without ever reaching generate.
            model=state.get("model") or settings.OPENAI_MODEL,
        )
    except (OperationalError, InterfaceError):
        # The turn is decided and, past the gate, paid for. A failed write -- a
        # full disk, a dropped connection, a lock or statement timeout -- turned
        # its answer into a 500 with no row; the visitor gets the answer and
        # stderr gets the error. (InterfaceError, a connection already closed,
        # is no DatabaseError, so catching that missed it.) Not all of
        # DatabaseError either: a broken schema, a revoked grant or a bad value
        # (ProgrammingError, IntegrityError, DataError) fails every turn the
        # same way, and caught it would leave ChatLog -- the only record of
        # spend -- empty behind 200s the canary cannot tell from health. Those
        # stay 500s, as does a bug in this node.
        logger.exception("ChatLog write failed; the turn is answered unlogged")
    return {}
