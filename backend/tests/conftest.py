import pytest


@pytest.fixture(autouse=True)
def clear_cache():
    """Throttle counters live in the real Redis and outlast a run, so without
    this a second local run inside a minute starts already rate-limited."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def chunk(db):
    from chat.models import ContentChunk

    return ContentChunk.objects.create(
        chunk_id="exp-majara#summary",
        record_id="exp-majara",
        kind="experience",
        title="Product Engineering intern",
        text="Built Python backend services.",
        content_hash="abc123",
        embedding=[0.0] * 1536,
    )
