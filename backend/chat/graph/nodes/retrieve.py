from pgvector.django import CosineDistance

from chat.openai_client import embed_query
from chat.graph.state import ChatState
from chat.models import ContentChunk

# Chunks scored, not records returned: TOP_K bounds how many *records* the
# search can surface, since each hit is expanded to its whole document below.
TOP_K = 6


def retrieve(state: ChatState) -> dict:
    # embed_query is imported into this module's namespace on purpose: that is
    # what lets each node's tests monkeypatch it without touching the network.
    vector = embed_query(state["condensed"])
    if vector is None:
        return {"retrieved": []}

    rows = (
        ContentChunk.objects.annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")[:TOP_K]
    )
    # dict.fromkeys dedupes while keeping nearest-first order, so the most
    # relevant document still leads the context after expansion.
    record_ids = list(dict.fromkeys(r.record_id for r in rows))
    if not record_ids:
        return {"retrieved": []}

    # Section-level matching finds the right document but hands over only the
    # paragraph that scored; the detail a visitor asks for usually sits in a
    # sibling section. Whole records cost a few thousand tokens on a corpus
    # this size and are what let the answer carry the content's own detail.
    # id order is ingestion order, which is document order: summary, then each
    # section as the chunker emitted it.
    siblings: dict[str, list[ContentChunk]] = {}
    for chunk in ContentChunk.objects.filter(record_id__in=record_ids).order_by("id"):
        siblings.setdefault(chunk.record_id, []).append(chunk)

    return {
        "retrieved": [
            {"chunk_id": c.chunk_id, "record_id": c.record_id,
             "title": c.title, "text": c.text}
            for rid in record_ids
            for c in siblings.get(rid, [])
        ]
    }
