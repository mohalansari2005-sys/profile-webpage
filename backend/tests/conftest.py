import pytest


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
