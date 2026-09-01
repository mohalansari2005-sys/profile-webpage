from django.conf import settings
from pydantic import BaseModel

from chat.graph.state import ChatState
from chat.openai_client import structured

REFUSAL = (
    "I can only answer from what Mohammed has written about his own work, "
    "and I don't have enough there to answer that. Try asking about his roles, "
    "the projects he's built, or the tools he works with."
)

PROMPT = """Answer the question using ONLY the numbered context below. Write in \
the third person about Mohammed.

Rules:
- Use only facts present in the context. Do not add, infer, or embellish.
- Let the question set the length. A factual question ("what is his major") \
takes a sentence or two; a question about how something was built, or what a \
role involved, should carry the specifics the context gives you -- the \
technologies, the constraints, the decisions and why they were made. Prefer \
the context's own detail over a summary of it.
- Do not pad. Length must come from facts in the context, never from restating \
the question or repeating a point in different words.
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
        "model": settings.OPENAI_MODEL,
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
        reason = "generation unavailable" if usage.get("api_error") else "unparseable response"
        return _refuse(reason, usage)
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
        "model": settings.OPENAI_MODEL,
    }
