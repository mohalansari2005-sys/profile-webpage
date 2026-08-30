import json

import pytest
from django.core.management import call_command


@pytest.fixture
def corpus_file(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({
        "groups": ["Build"],
        "tools": [{"id": "python", "label": "Python", "group": "Build"}],
        "records": [{
            "id": "exp-a", "kind": "experience", "title": "Engineer", "org": "Acme",
            "period": "2025", "summary": "Did things.", "tools": ["python"],
            "body": "## Detail\n\nProse here.", "source": "experience/a.md",
        }],
    }))
    return path


@pytest.fixture
def fake_embeddings(monkeypatch):
    calls = {"n": 0}
    from chat.management.commands import ingest_content as cmd

    def fake(texts):
        calls["n"] += len(texts)
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(cmd, "embed_documents", fake)
    return calls


def test_ingest_creates_a_chunk_per_section(db, corpus_file, fake_embeddings):
    from chat.models import ContentChunk

    call_command("ingest_content", corpus=str(corpus_file))
    assert set(ContentChunk.objects.values_list("chunk_id", flat=True)) == {
        "exp-a#summary", "exp-a#detail",
    }
    assert fake_embeddings["n"] == 2


def test_reingesting_unchanged_content_embeds_nothing(db, corpus_file, fake_embeddings):
    call_command("ingest_content", corpus=str(corpus_file))
    before = fake_embeddings["n"]
    call_command("ingest_content", corpus=str(corpus_file))
    assert fake_embeddings["n"] == before


def test_changed_text_is_re_embedded(db, corpus_file, fake_embeddings):
    from chat.models import ContentChunk

    call_command("ingest_content", corpus=str(corpus_file))
    data = json.loads(corpus_file.read_text())
    data["records"][0]["summary"] = "Did other things."
    corpus_file.write_text(json.dumps(data))
    before = fake_embeddings["n"]
    call_command("ingest_content", corpus=str(corpus_file))
    assert fake_embeddings["n"] == before + 1
    assert ContentChunk.objects.get(chunk_id="exp-a#summary").text == "Did other things."


def test_orphaned_chunks_are_deleted(db, corpus_file, fake_embeddings):
    from chat.models import ContentChunk

    call_command("ingest_content", corpus=str(corpus_file))
    data = json.loads(corpus_file.read_text())
    data["records"][0]["body"] = ""
    corpus_file.write_text(json.dumps(data))
    call_command("ingest_content", corpus=str(corpus_file))
    assert not ContentChunk.objects.filter(chunk_id="exp-a#detail").exists()


def test_a_missing_corpus_file_fails_loudly(db, tmp_path):
    from django.core.management.base import CommandError

    missing = tmp_path / "nope.json"
    with pytest.raises(CommandError) as e:
        call_command("ingest_content", corpus=str(missing))
    # Names the path it actually looked for, and how to produce it.
    assert str(missing) in str(e.value)
    assert "npm run content" in str(e.value)
