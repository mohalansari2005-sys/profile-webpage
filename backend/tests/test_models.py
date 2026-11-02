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


def test_the_migration_marks_past_outages_by_their_exact_labels(db):
    """Rows logged before ChatLog.unavailable existed said so only in
    refusal_reason. A refusal whose free text merely ends the same way stays a
    refusal."""
    from importlib import import_module

    from django.apps import apps

    from chat.models import ChatLog

    migration = import_module("chat.migrations.0002_chatlog_unavailable_synthetic")
    reasons = ["generation unavailable", "retrieval unavailable", "condense unavailable",
               "general: that product is unavailable", "", "request rejected"]
    for reason in reasons:
        ChatLog.objects.create(ip_hash="h" * 64, question="q", refused=bool(reason),
                               refusal_reason=reason, latency_ms=1, model="m")
    migration.mark_past_outages(apps, None)
    flagged = dict(ChatLog.objects.values_list("refusal_reason", "unavailable"))
    assert flagged == {reason: reason in migration.OUTAGE_REASONS for reason in reasons}
    assert sum(flagged.values()) == 3


def test_code_from_before_the_flags_can_still_log_a_turn(db):
    """`migrate` never unapplies a migration whose file is gone, so after a
    revert of chat.0002 the old code runs against these columns and inserts
    without them. Their database default is what keeps that from being a 500
    on every chat turn."""
    from django.db import connection

    from chat.models import ChatLog

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO chat_chatlog (created_at, ip_hash, question, condensed_question,"
            " answer, refused, refusal_reason, retrieved_chunk_ids, used_chunk_ids,"
            " latency_ms, model) VALUES (now(), %s, 'q', '', '', false, '', '[]', '[]', 1, 'm')",
            ["h" * 64],
        )
    row = ChatLog.objects.get()
    assert (row.unavailable, row.synthetic) == (False, False)


def test_a_query_cannot_wait_forever(db):
    """Under gthread nothing else ends a stuck query: gunicorn's --timeout no
    longer kills a slow request, and the turn budget covers OpenAI only."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SHOW statement_timeout")
        statement = cursor.fetchone()[0]
        cursor.execute("SHOW lock_timeout")
        lock = cursor.fetchone()[0]
    assert (statement, lock) == ("15s", "5s")
