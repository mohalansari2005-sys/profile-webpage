import hashlib
import re
import unicodedata
from dataclasses import dataclass

HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    record_id: str
    kind: str
    title: str
    text: str
    content_hash: str


def slugify(heading: str) -> str:
    """ASCII-fold what folds, drop what doesn't, hyphenate the rest.

    Arabic headings fold to nothing, so a non-empty fallback matters --
    content/experience/seet.md has "SEET (صيت)" in its prose.
    """
    folded = unicodedata.normalize("NFKD", heading).encode("ascii", "ignore").decode()
    # Drop apostrophes before hyphenating so contractions close up:
    # "What I'd do" -> what-id-do, not what-i-d-do.
    folded = folded.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")
    return slug or "section"


def _sections(body: str) -> list[tuple[str, str]]:
    """(heading, prose) pairs. Prose before the first heading gets heading ''."""
    matches = list(HEADING.finditer(body))
    if not matches:
        return [("", body.strip())] if body.strip() else []

    out = []
    preamble = body[: matches[0].start()].strip()
    if preamble:
        out.append(("", preamble))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out.append((m.group(1), body[m.end() : end].strip()))
    return out


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def chunk_record(record: dict) -> list[Chunk]:
    record_id, kind, title = record["id"], record["kind"], record["title"]

    def make(suffix: str, text: str) -> Chunk:
        return Chunk(
            chunk_id=f"{record_id}#{suffix}", record_id=record_id, kind=kind,
            title=title, text=text, content_hash=_hash(text),
        )

    chunks = []
    summary = (record.get("summary") or "").strip()
    if summary:
        chunks.append(make("summary", summary))

    used: set[str] = {"summary"}
    for heading, prose in _sections(record.get("body") or ""):
        if not prose:
            continue
        base = slugify(heading) if heading else "body"
        suffix, n = base, 1
        while suffix in used:
            n += 1
            suffix = f"{base}-{n}"
        used.add(suffix)
        chunks.append(make(suffix, f"{heading}\n\n{prose}".strip() if heading else prose))

    return chunks
