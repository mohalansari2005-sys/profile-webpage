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


@pytest.fixture
def record_with_sections(db):
    """One record whose summary is a poor vector match and whose second section
    is the good one -- the shape that made answers read as summaries."""
    from chat.models import ContentChunk

    for i, (cid, vec_index) in enumerate([
        ("proj-keyraa#summary", 5),
        ("proj-keyraa#what-the-work-actually-involved", 0),
    ]):
        v = [0.0] * 1536
        v[vec_index] = 1.0
        ContentChunk.objects.create(
            chunk_id=cid, record_id="proj-keyraa", kind="projects",
            title="Keyraa", text=f"section {i}", content_hash=f"h{i}", embedding=v,
        )


def test_a_matched_record_brings_its_whole_document(db, record_with_sections, monkeypatch):
    """Retrieval picks records; generate reads them whole. Handing over only the
    section that matched is what made answers look summarized -- the detail the
    visitor asked for often sits in a sibling section that scored lower."""
    from chat.graph.nodes import retrieve as node

    target = [0.0] * 1536
    target[0] = 1.0  # matches the section, not the summary
    monkeypatch.setattr(node, "embed_query", lambda q: target)

    ids = [c["chunk_id"] for c in node.retrieve({"condensed": "how was it built"})["retrieved"]]
    assert ids == ["proj-keyraa#summary", "proj-keyraa#what-the-work-actually-involved"]


def test_records_stay_in_relevance_order(db, three_chunks, record_with_sections, monkeypatch):
    """Whole records are appended nearest-first, so the most relevant document
    leads the context even after expansion."""
    from chat.graph.nodes import retrieve as node

    target = [0.0] * 1536
    target[1] = 1.0  # exp-b is nearest
    monkeypatch.setattr(node, "embed_query", lambda q: target)

    out = node.retrieve({"condensed": "who is the analyst"})
    assert out["retrieved"][0]["chunk_id"] == "exp-b#summary"
    # every chunk of a matched record appears exactly once
    assert len(set(c["chunk_id"] for c in out["retrieved"])) == len(out["retrieved"])
