from pydantic import BaseModel

from chat.gemini import structured
from chat.graph.state import ChatState

PROMPT = """Rewrite the user's latest message as a standalone question that makes \
sense without the conversation. Resolve pronouns and references using the history. \
Do not answer it. Do not add information that is not in the conversation.

Conversation so far:
{history}

Latest message: {question}"""


class Standalone(BaseModel):
    standalone_question: str


def condense(state: ChatState) -> dict:
    question = state["question"]
    history = state.get("history") or []
    if not history:
        # Most first turns. No model call, no quota spent, no latency.
        return {"condensed": question}

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    parsed, _ = structured(
        PROMPT.format(history=transcript, question=question),
        Standalone,
        fast=True,
    )
    rewritten = (parsed.standalone_question or "").strip() if parsed else ""
    return {"condensed": rewritten or question}
