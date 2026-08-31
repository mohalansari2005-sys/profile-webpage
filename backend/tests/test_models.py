import pytest
from django.db import IntegrityError


def test_chunk_id_is_unique(db, chunk):
    from chat.models import ContentChunk

    with pytest.raises(IntegrityError):
        ContentChunk.objects.create(
            chunk_id="exp-majara#summary", record_id="exp-majara", kind="experience",
            title="dupe", text="dupe", content_hash="x", embedding=[0.0] * 1536,
        )


def test_embedding_round_trips_at_1536_dimensions(db, chunk):
    from chat.models import ContentChunk

    stored = ContentChunk.objects.get(chunk_id="exp-majara#summary")
    assert len(stored.embedding) == 1536


def test_chatlog_stores_a_hash_never_a_raw_ip(db):
    from chat.models import ChatLog, hash_ip

    log = ChatLog.objects.create(
        ip_hash=hash_ip("203.0.113.9"), question="q", condensed_question="q",
        answer="a", refused=False, retrieved_chunk_ids=["exp-majara#summary"],
        used_chunk_ids=["exp-majara#summary"], latency_ms=12, model="gpt-model",
    )
    assert "203.0.113.9" not in log.ip_hash
    assert len(log.ip_hash) == 64


def test_hash_ip_is_stable_and_salted(settings):
    from chat.models import hash_ip

    settings.IP_HASH_SALT = "salt-a"
    a = hash_ip("203.0.113.9")
    assert hash_ip("203.0.113.9") == a
    settings.IP_HASH_SALT = "salt-b"
    assert hash_ip("203.0.113.9") != a
