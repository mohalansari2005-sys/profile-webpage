import hashlib

from django.conf import settings
from django.db import models
from pgvector.django import VectorField


def hash_ip(ip: str) -> str:
    """Salted SHA-256. A raw IP must never reach the database."""
    return hashlib.sha256(f"{settings.IP_HASH_SALT}:{ip}".encode()).hexdigest()


class ContentChunk(models.Model):
    chunk_id = models.CharField(max_length=200, unique=True)
    record_id = models.CharField(max_length=100, db_index=True)
    kind = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    text = models.TextField()
    content_hash = models.CharField(max_length=64)
    embedding = VectorField(dimensions=settings.EMBED_DIMENSIONS)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.chunk_id


class ChatLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_hash = models.CharField(max_length=64)
    question = models.TextField()
    condensed_question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    refused = models.BooleanField(default=False)
    refusal_reason = models.CharField(max_length=200, blank=True)
    retrieved_chunk_ids = models.JSONField(default=list)
    used_chunk_ids = models.JSONField(default=list)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    latency_ms = models.IntegerField()
    model = models.CharField(max_length=60)
