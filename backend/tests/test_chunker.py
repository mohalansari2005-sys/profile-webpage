from chat.ingestion.chunker import chunk_record

TOOL_LABELS = {"python": "Python", "rest-apis": "REST APIs"}

RECORD = {
    "id": "exp-majara",
    "kind": "experience",
    "title": "Product Engineering intern",
    "org": "Majara — Riyadh, hybrid",
    "period": "Nov 2025 — Present",
    "summary": "Built Python backend services and REST APIs.",
    "body": "## What the work actually involved\n\nI joined as an intern.\n\n"
            "## What I'd do differently\n\nWrite the tests first.",
}


def test_summary_becomes_its_own_chunk():
    chunks = chunk_record(RECORD)
    summary = next(c for c in chunks if c.chunk_id == "exp-majara#summary")
    assert summary.text.endswith("\n\nBuilt Python backend services and REST APIs.")
    assert summary.record_id == "exp-majara"
    assert summary.kind == "experience"


def test_the_summary_chunk_carries_the_record_s_fields():
    """The page shows each record's title, organisation, dates and tools. Kept
    out of the chunk text, the bot could not say when he worked anywhere."""
    record = dict(RECORD, tools=["python", "rest-apis"], repo="https://github.com/a/b")
    summary = chunk_record(record, TOOL_LABELS)[0]
    assert summary.text == (
        "Title: Product Engineering intern\n"
        "Organisation: Majara — Riyadh, hybrid\n"
        "Period: Nov 2025 — Present\n"
        "Tools: Python, REST APIs\n"
        "Repository: https://github.com/a/b\n"
        "\n"
        "Built Python backend services and REST APIs."
    )


def test_empty_fields_are_left_out_of_the_header():
    summary = chunk_record(dict(RECORD, org="", period="", tools=[]), TOOL_LABELS)[0]
    assert summary.text == ("Title: Product Engineering intern\n\n"
                            "Built Python backend services and REST APIs.")


def test_a_tool_without_a_label_keeps_its_id():
    summary = chunk_record(dict(RECORD, tools=["cobol"]), TOOL_LABELS)[0]
    assert "Tools: cobol\n" in summary.text


def test_sections_do_not_repeat_the_header():
    """Retrieval hands generate the whole record, summary included, so the
    fields reach the prompt once; repeated, they would dilute every section's
    embedding."""
    for chunk in chunk_record(RECORD)[1:]:
        assert "Period:" not in chunk.text


def test_each_heading_becomes_a_chunk_with_a_readable_id():
    ids = [c.chunk_id for c in chunk_record(RECORD)]
    assert ids == [
        "exp-majara#summary",
        "exp-majara#what-the-work-actually-involved",
        "exp-majara#what-id-do-differently",
    ]


def test_section_text_keeps_its_heading_for_context():
    chunks = chunk_record(RECORD)
    section = next(c for c in chunks if c.chunk_id.endswith("#what-the-work-actually-involved"))
    assert section.text.startswith("What the work actually involved")
    assert "I joined as an intern." in section.text


def test_prose_before_the_first_heading_is_not_dropped():
    record = dict(RECORD, body="Loose opening prose.\n\n## A heading\n\nMore.")
    ids = [c.chunk_id for c in chunk_record(record)]
    assert "exp-majara#body" in ids


def test_empty_sections_are_skipped():
    record = dict(RECORD, body="## Empty\n\n## Real\n\nHas text.")
    ids = [c.chunk_id for c in chunk_record(record)]
    assert "exp-majara#empty" not in ids
    assert "exp-majara#real" in ids


def test_duplicate_headings_get_distinct_ids():
    record = dict(RECORD, body="## Notes\n\nOne.\n\n## Notes\n\nTwo.")
    ids = [c.chunk_id for c in chunk_record(record)]
    assert ids.count("exp-majara#notes") == 1
    assert "exp-majara#notes-2" in ids


def test_the_summary_hash_follows_the_record_s_fields():
    """A changed date must re-embed the summary, or the bot keeps the old one."""
    a = chunk_record(RECORD)[0]
    b = chunk_record(dict(RECORD, period="changed"))[0]
    c = chunk_record(dict(RECORD, summary="different text"))[0]
    assert len({a.content_hash, b.content_hash, c.content_hash}) == 3


def test_a_section_hash_tracks_its_prose_and_nothing_else():
    a = chunk_record(RECORD)[1]
    b = chunk_record(dict(RECORD, period="changed", title="changed"))[1]
    c = chunk_record(dict(RECORD, body=RECORD["body"].replace("an intern", "a dev")))[1]
    assert a.content_hash == b.content_hash
    assert a.content_hash != c.content_hash


def test_non_ascii_headings_survive_slugging():
    record = dict(RECORD, body="## SEET (صيت) — the agency\n\nText.")
    ids = [c.chunk_id for c in chunk_record(record)]
    assert any(i.startswith("exp-majara#seet") for i in ids)


def test_a_record_with_no_body_still_yields_its_summary():
    chunks = chunk_record(dict(RECORD, body=""))
    assert [c.chunk_id for c in chunks] == ["exp-majara#summary"]
