from pydantic import BaseModel

from chat.gemini import structured
from chat.graph.state import ChatState

REFUSAL = (
    "I can only answer from what Mohammed has written about his own work, "
    "and I don't have enough there to answer that. Try asking about his roles, "
    "the projects he's built, or the tools he works with."
)

PROMPT = """Answer the question using ONLY the numbered context below. Write in \
the third person about Mohammed. Two or three sentences.

Rules:
- Use only facts present in the context. Do not add, infer, or embellish.
- List in used_chunk_ids the exact chunk ids you drew from. Never invent an id.
- If the context does not contain the answer, set sufficient to false.

Context:
{context}

Question: {question}"""


class Answer(BaseModel):
    answer: str
    used_chunk_ids: list[str]
    sufficient: bool


def _refuse(reason: str, usage: dict | None = None) -> dict:
    return {
        "answer": REFUSAL, "used_chunk_ids": [], "sources": [],
        "refused": True, "refusal_reason": reason, "usage": usage or {},
    }


def generate(state: ChatState) -> dict:
    retrieved = state.get("retrieved") or []
    if not retrieved:
        return _refuse("nothing retrieved")

    context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in retrieved)
    parsed, usage = structured(
        PROMPT.format(context=context, question=state["condensed"]), Answer
    )

    if parsed is None:
        return _refuse("unparseable response", usage)
    if not parsed.sufficient:
        return _refuse("insufficient context", usage)

    retrieved_ids = {c["chunk_id"] for c in retrieved}
    if not set(parsed.used_chunk_ids) <= retrieved_ids:
        # The model cited something retrieval never returned. Whatever it wrote
        # is not grounded in the corpus, so it does not leave the server.
        return _refuse("ungrounded citation", usage)

    by_chunk = {c["chunk_id"]: c for c in retrieved}
    sources: list[dict[str, str]] = []
    for cid in parsed.used_chunk_ids:
        chunk = by_chunk[cid]
        entry = {"record_id": chunk["record_id"], "title": chunk["title"]}
        if entry not in sources:
            sources.append(entry)

    return {
        "answer": parsed.answer, "used_chunk_ids": parsed.used_chunk_ids,
        "sources": sources, "refused": False, "refusal_reason": "", "usage": usage,
    }
