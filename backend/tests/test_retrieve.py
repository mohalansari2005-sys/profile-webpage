import pytest


@pytest.fixture
def three_chunks(db):
    from chat.models import ContentChunk

    def unit(index: int) -> list[float]:
        v = [0.0] * 1536
        v[index] = 1.0
        return v

    for i, (cid, title) in enumerate([
        ("exp-a#summary", "Engineer"),
        ("exp-b#summary", "Analyst"),
        ("proj-c#summary", "Booking"),
    ]):
        ContentChunk.objects.create(
            chunk_id=cid, record_id=cid.split("#")[0], kind="experience",
            title=title, text=f"text {i}", content_hash=str(i), embedding=unit(i),
        )


def test_retrieve_returns_nearest_first(db, three_chunks, monkeypatch):
    from chat.graph.nodes import retrieve as node

    target = [0.0] * 1536
    target[1] = 1.0
    monkeypatch.setattr(node, "embed_query", lambda q: target)

    out = node.retrieve({"condensed": "who is the analyst"})
    assert out["retrieved"][0]["chunk_id"] == "exp-b#summary"
    assert out["retrieved"][0]["title"] == "Analyst"


def test_retrieve_is_capped(db, three_chunks, monkeypatch):
    from chat.graph.nodes import retrieve as node

    monkeypatch.setattr(node, "embed_query", lambda q: [0.0] * 1536)
    monkeypatch.setattr(node, "TOP_K", 2)
    assert len(node.retrieve({"condensed": "anything"})["retrieved"]) == 2


def test_retrieve_embeds_the_condensed_question_not_the_raw_one(db, three_chunks, monkeypatch):
    from chat.graph.nodes import retrieve as node

    seen = {}

    def fake(q):
        seen["q"] = q
        return [0.0] * 1536

    monkeypatch.setattr(node, "embed_query", fake)
    node.retrieve({"question": "and there?", "condensed": "what did he build at Majara"})
    assert seen["q"] == "what did he build at Majara"


def test_a_failed_embed_retrieves_nothing_instead_of_crashing(db, three_chunks, monkeypatch):
    from chat.graph.nodes import retrieve as node

    monkeypatch.setattr(node, "embed_query", lambda q: None)
    assert node.retrieve({"condensed": "anything"}) == {"retrieved": []}
