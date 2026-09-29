from pydantic import BaseModel

from chat.graph.state import ChatState
from chat.language import NAME_GLOSSARY, is_arabic, normalize_names
from chat.openai_client import structured

PROMPT = """Rewrite the user's latest message as a standalone question that makes \
sense without the conversation. Resolve pronouns and references using the history. \
Do not answer it. Do not add information that is not in the conversation. Keep \
the latest message's language: never translate it (an Arabic message stays \
Arabic).

Also give english_query: the same standalone question in English, to search an \
English portfolio. Keep proper names (Majara, SEET, Keyraa, tool names) in Latin \
letters. If the question is already English, repeat it.

{glossary}

Conversation so far:
{history}

Latest message: {question}"""


class Standalone(BaseModel):
    standalone_question: str
    english_query: str = ""


def condense(state: ChatState) -> dict:
    # Known names first, deterministically: every later node then reads
    # "Majara", not a transliteration it might take for another word.
    question = normalize_names(state["question"])
    history = state.get("history") or []
    # An Arabic question needs the model even on a first turn: the portfolio is
    # English, and searching it with Arabic text retrieves poorly.
    if not history and not is_arabic(question):
        # Most first turns. No model call, no quota spent, no latency.
        return {"condensed": question}

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history) or "(none)"
    parsed, usage = structured(
        PROMPT.format(glossary=NAME_GLOSSARY, history=transcript, question=question),
        Standalone,
        fast=True,
    )
    rewritten = normalize_names((parsed.standalone_question or "").strip()) if parsed else ""
    condensed = rewritten or question
    english = (parsed.english_query or "").strip() if parsed else ""
    # Billable even when the rewrite is discarded, so it is carried, not dropped.
    return {"condensed": condensed, "search_query": english or condensed, "usage": usage}
