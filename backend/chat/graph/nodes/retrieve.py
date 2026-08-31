from pgvector.django import CosineDistance

from chat.openai_client import embed_query
from chat.graph.state import ChatState
from chat.models import ContentChunk

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
    return {
        "retrieved": [
            {"chunk_id": r.chunk_id, "record_id": r.record_id,
             "title": r.title, "text": r.text}
            for r in rows
        ]
    }
