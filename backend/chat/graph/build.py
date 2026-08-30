from langgraph.graph import END, StateGraph

from chat.graph.nodes.condense import condense
from chat.graph.nodes.generate import generate
from chat.graph.nodes.log import log
from chat.graph.nodes.relevance import relevance, route
from chat.graph.nodes.retrieve import retrieve
from chat.graph.state import ChatState

REFUSAL_OUT_OF_SCOPE = (
    "I only answer questions about Mohammed's work — his roles, the projects "
    "he's built, and the tools he uses. Ask me about one of those."
)


def _mark_refused(state: ChatState) -> dict:
    """The not_in_scope edge skips generate, so the refusal text is set here
    rather than in log -- a logging node should not own user-facing copy."""
    return {"answer": REFUSAL_OUT_OF_SCOPE, "refused": True, "sources": [],
            "used_chunk_ids": []}


def build_graph():
    g = StateGraph(ChatState)
    g.add_node("condense", condense)
    g.add_node("relevance", relevance)
    g.add_node("refuse", _mark_refused)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("log", log)

    g.set_entry_point("condense")
    g.add_edge("condense", "relevance")
    g.add_conditional_edges("relevance", route, {"retrieve": "retrieve", "log": "refuse"})
    g.add_edge("refuse", "log")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "log")
    g.add_edge("log", END)
    return g.compile()
