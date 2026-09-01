import hashlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from chat.ingestion.chunker import chunk_record
from chat.ingestion.loader import CorpusMissing, load_corpus
from chat.models import ContentChunk
from chat.openai_client import embed_documents


class Command(BaseCommand):
    help = "Ingest the generated corpus into ContentChunk. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--corpus", default=str(settings.CORPUS_PATH))
        parser.add_argument("--batch", type=int, default=20)

    def handle(self, *args, **options):
        try:
            corpus = load_corpus(options["corpus"])
        except CorpusMissing as e:
            raise CommandError(str(e))

        wanted = [c for record in corpus["records"] for c in chunk_record(record)]
        existing = dict(ContentChunk.objects.values_list("chunk_id", "content_hash"))

        # The stored hash covers the text AND the model that embedded it.
        # Vectors from two different embedding models are not comparable, so a
        # model change has to invalidate every row -- and the text alone cannot
        # see that. Without this, switching models leaves the old vectors in
        # place and retrieval degrades silently instead of failing.
        def stamp(chunk):
            return hashlib.sha256(
                f"{settings.OPENAI_EMBED_MODEL}:{chunk.content_hash}".encode()
            ).hexdigest()

        # Hash comparison is what makes re-running free.
        changed = [c for c in wanted if existing.get(c.chunk_id) != stamp(c)]
        for i in range(0, len(changed), options["batch"]):
            batch = changed[i : i + options["batch"]]
            vectors = embed_documents([c.text for c in batch])
            for chunk, vector in zip(batch, vectors):
                ContentChunk.objects.update_or_create(
                    chunk_id=chunk.chunk_id,
                    defaults={
                        "record_id": chunk.record_id, "kind": chunk.kind,
                        "title": chunk.title, "text": chunk.text,
                        "content_hash": stamp(chunk), "embedding": vector,
                    },
                )

        wanted_ids = {c.chunk_id for c in wanted}
        orphans = ContentChunk.objects.exclude(chunk_id__in=wanted_ids)
        deleted = orphans.count()
        orphans.delete()

        self.stdout.write(
            f"{len(wanted)} chunks; {len(changed)} embedded; {deleted} orphans removed"
        )
