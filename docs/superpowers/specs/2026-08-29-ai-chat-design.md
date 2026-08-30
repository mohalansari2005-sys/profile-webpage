# AI chat over my experience — design

**Date:** 2026-08-29
**Status:** approved, not yet implemented
**Supersedes:** `portfolio-ai-chat-prompts-v2.md` (referenced by `CLAUDE.md`, never existed)


## Context

Recruiters reading the portfolio can only learn what the page shows. The goal is a
chat surface where they ask "what did he actually build at Majara?" and get an
answer grounded strictly in my own content, refusing anything outside it.

Per `CLAUDE.md`, this feature is a deliberate learning exercise — RAG, agent
orchestration, and self-hosted ops are chosen on purpose, not accidental
complexity. The "keep it minimal" instinct does not apply to its scope.

**Four things about the current repo shape this plan:**

1. **It is not a monorepo.** The Next.js app is at the repo root, not `/frontend`.
2. **`output: "export"`** — no server runtime. The browser calls Django directly,
   cross-origin. The API origin must be a `NEXT_PUBLIC_` build-time variable.
3. **`portfolio-ai-chat-prompts-v2.md`, cited by `CLAUDE.md`, does not exist** —
   not in the repo, git history, or on disk. This plan is now that document's job.
4. **The corpus today is ~500 words** (`lib/content.ts`: 2 roles, 1 project).
   RAG over that retrieves everything, every time, and demonstrates nothing.
   Resolved by decision D1 below.

**Decisions taken during brainstorming:**

| # | Decision |
|---|---|
| D1 | One markdown corpus under `content/` is the source of truth for **both** the bot and the site; `lib/content.ts` becomes generated at build time. No drift. |
| D2 | Repo restructure to `/frontend` + `/backend` happens on its **own branch first**, reviewed and merged before any feature work. |
| D3 | Multi-turn, **client holds history**. Django stays stateless — no session table. Adds a `condense` node to rewrite follow-ups into standalone queries. |
| D4 | **Buffered** JSON response, not SSE. Keeps gunicorn/WSGI and DRF; streaming can be added later by changing only the final node's transport. |
| D5 | Grounding is **enforced in Python**, not prompted: both the relevance gate and the generate step return schema-validated JSON, and cited chunk IDs are checked against what retrieval actually returned. |
| D6 | **Local-only.** docker-compose runs on localhost. No VPS, no domain, no TLS. Production deploy is a later, separate piece of work. |
| D7 | **Gemini for everything** — generation *and* embeddings, on the free tier. One provider, one API key, one SDK (`google-genai`). No Anthropic dependency, no second account. |
| D8 | **The API key never leaves the server.** See "Secrets" below — this is the reason the Django backend exists at all rather than calling Gemini from the browser. |

---

## Secrets — how keys stay out of the repo and out of the bundle

The single most dangerous mistake available in this architecture is putting the
Gemini key somewhere the browser can read it. Static-export Next.js inlines every
`NEXT_PUBLIC_*` variable into JavaScript that ships to the client and is readable
by anyone who opens devtools. `NEXT_PUBLIC_CHAT_API_URL` is fine — it is just a
URL. **A `NEXT_PUBLIC_GEMINI_API_KEY` would publish the key to the world.** The
key lives only in the Django container; the browser talks to Django, and Django
talks to Gemini.

Concretely:

- **`backend/.env`** (never committed) holds `GEMINI_API_KEY`,
  `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `IP_HASH_SALT`.
- **`backend/.env.example`** is committed with placeholder values only, so the
  required variable names are documented without the values.
- **`.gitignore` needs a fix, not just a check.** The existing rule is `.env*`,
  which is unanchored and so already covers `backend/.env` after the restructure —
  but it *also* silently swallows `.env.example`. Add `!.env.example` so the
  template can actually be committed.
- **`backend/.dockerignore`** must list `.env` so the key is never baked into an
  image layer. Compose injects it at runtime via `env_file:`; no key literal ever
  appears in `docker-compose.yml` or the `Dockerfile`.
- **`config/settings.py`** reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and
  `GEMINI_API_KEY` from the environment with **no fallback literals**, and raises
  at startup if `GEMINI_API_KEY` is missing — a clear boot failure beats a
  confusing 500 on the first question.
- **Logging never records the key**, and `ChatLog` stores a salted SHA-256
  `ip_hash`, never a raw IP address.

**Verify before the first commit that touches secrets.** Use `check-ignore -q` and
read the *exit code* — verified against this repo, both claims above hold:

```
git check-ignore -q backend/.env          # exit 0  = ignored        (want this)
git check-ignore -q backend/.env.example  # exit 1  = committable    (want this)
```

> Do **not** verify with `check-ignore -v`. It exits 0 whenever *any* rule matches,
> including the `!.env.example` negation, so it reports success for both files and
> looks like the negation failed. `git add --dry-run <path>` is the other
> unambiguous check: it prints `add '<path>'` or tells you the path is ignored.

Then
`docker run --rm <image> printenv | grep -i gemini` must come back empty, proving
the key is not in the image. Finally, grep the built frontend for the key value:
`grep -r "$GEMINI_API_KEY" frontend/out/` must return nothing.

---

## Branches

Four branches, each independently reviewable. `main` never sees half-finished work.

### Branch 1 — `chore/monorepo-layout`

Pure plumbing, zero feature code. Move everything currently at the repo root into
`frontend/`; create empty `backend/` and `content/`.

Moves: `app/`, `components/`, `lib/`, `public/`, `package.json`,
`package-lock.json`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs`,
`eslint.config.mjs`, `components.json`, `next-env.d.ts`, `AGENTS.md`.

- `.gitignore` paths are root-anchored (`/node_modules`, `/.next/`, `/out/`) and
  must be de-anchored (`node_modules/`, `.next/`, `out/`) or re-prefixed. Add the
  `!.env.example` negation described above in the same pass.
- `README.md` and `CLAUDE.md` stay at the root; both need path updates.
- **Vercel's Root Directory setting must change to `frontend`** — a dashboard
  change, not a code change. Nothing else about the deploy changes.
- `AGENTS.md` is regenerated by `next dev`; it will reappear inside `frontend/`.

**Verify:** `cd frontend && npm run build` succeeds and `out/` is structurally
identical to today's; `npm run lint` clean; the Vercel preview deploy renders the
current site unchanged.

---

### Branch 2 — `feat/content-pipeline`

Make the markdown corpus real and generate `lib/content.ts` from it. The site must
look **exactly** the same when this branch lands — that identity is the test.

```
content/
  tools.yml                       # the Tool[] registry: id, label, group
  experience/majara.md
  experience/seet.md
  projects/corporate-hotel-booking.md
  about/bio.md
  faq/*.md                        # recruiter questions the page never answers
```

Each record carries the page's fields in frontmatter and the bot's depth in the body:

```markdown
---
id: exp-majara
kind: experience
title: Product Engineer
org: Majara — Riyadh, hybrid
period: Nov 2025 — Present
tools: [python, javascript, rest-apis, langchain, systems-analysis, agile, sdlc, b2b]
summary: >
  Built and integrated Python backend services and REST APIs for a B2B product...
---

## What I actually built
Prose the page never shows. This is what retrieval answers from.
```

**`frontend/scripts/build-content.ts`** reads `content/`, validates, and writes
`frontend/lib/content.ts`. Wired as an npm `prebuild` script; the generated file
stays committed so `next dev` works with no extra step.

Validation is the point — today a `tools` key matching no `Tool.id` renders
nothing, **silently** (documented as a footgun in `README.md`). The generator
turns that into a build error. Same for duplicate `id`s and missing frontmatter.

Types (`Tool`, `WorkRecord`, `ToolGroup`) and the `toolById` map keep their
current shape exactly, so `hero.tsx`, `work.tsx`, `about.tsx` need no changes.

- **New dev dependency:** `gray-matter` (frontmatter parsing). One small, standard
  package; the alternative is hand-rolling a YAML front-matter splitter.

**Verify:** `npm run build`, then diff the generated `lib/content.ts` against the
current committed file — the records must be equivalent. Load the page and confirm
the tool-strip join still highlights the same rows. Break a `tools` key on purpose
and confirm the build fails with a useful message.

---

### Branch 3 — `feat/chat-backend`

```
backend/
  Dockerfile  .dockerignore  pyproject.toml  manage.py  .env.example
  config/          settings.py  urls.py  wsgi.py
  chat/
    models.py                 # ContentChunk, ChatLog
    views.py  serializers.py  throttling.py
    gemini.py                 # one client, shared by embed + generate
    graph/
      state.py  build.py
      nodes/ condense.py  relevance.py  retrieve.py  generate.py  log.py
    ingestion/ loader.py  chunker.py  embedder.py
    management/commands/ingest_content.py
  tests/
docker-compose.yml            # web + db + redis
```

#### Data model

`ContentChunk` — `chunk_id` (unique, e.g. `exp-majara#what-i-built`), `record_id`,
`kind`, `title`, `text`, `content_hash`, `embedding VectorField(dimensions=1536)`.

> **Dimension choice matters.** `gemini-embedding-001` returns 3072 dims by
> default, but **pgvector cannot index any vector above 2000 dims** — no hnsw, no
> ivfflat. Request `output_dimensionality=1536` (the model supports Matryoshka
> truncation) and re-normalize the truncated vector before storing. Query with
> cosine distance (`<=>`). At this corpus size an exact scan is instant either
> way, but 1536 keeps the index option open instead of foreclosing it.

`ChatLog` — timestamp, **`ip_hash`** (salted SHA-256, never the raw IP),
`question`, `condensed_question`, `answer`, `refused`, `refusal_reason`,
`retrieved_chunk_ids`, `used_chunk_ids`, token counts, `latency_ms`, `model`.

#### Ingestion — `python manage.py ingest_content`

Reads the same `content/` tree Branch 2 generates the site from. Chunks per
section: the frontmatter summary is one chunk, each `##` heading in the body is
another, giving readable IDs like `exp-majara#summary`. Embeds with task type
**`RETRIEVAL_DOCUMENT`** (queries use `RETRIEVAL_QUERY` — using one type for both
is a common bug that quietly degrades retrieval). Skips chunks whose
`content_hash` is unchanged and deletes orphans, so re-running is idempotent and
free.

#### The graph

```
condense ──> relevance ──in_scope──> retrieve ──> generate ──> log ──> END
                   └────not_in_scope──────────────────────────> log ──> END
```

Both paths reach `log` — refusals are the most interesting analytics.
`condense` short-circuits with no model call when `history` is empty, which is
most first turns.

All three model calls go through `google-genai` against a Gemini free-tier model
(`gemini-2.5-flash` unless the current free-tier lineup says otherwise — confirm
at implementation time; model names and quotas change). `condense` and
`relevance` are cheap classifier calls and set `thinking_budget=0`; `generate`
leaves thinking on its default.

#### Grounding (D5) — enforced, not prompted

Gemini's `response_schema` guarantees the shape, so no refusal has to be parsed
out of prose:

```python
class Relevance(BaseModel):
    in_scope: bool
    reason: str

class Answer(BaseModel):
    answer: str
    used_chunk_ids: list[str]
    sufficient: bool

resp = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=Answer,
    ),
)
a = resp.parsed

# generate node:
if not a.sufficient or not set(a.used_chunk_ids) <= retrieved_ids:
    return REFUSAL
```

An invented chunk ID or `sufficient=False` becomes a refusal in Python before the
response ever leaves the server.

#### API

```
POST /api/chat/
{ "question": str, "history": [{"role": "user"|"assistant", "content": str}] }

200 { "answer": str,
      "sources": [{"record_id": "exp-majara", "title": "Product Engineer, Majara"}],
      "refused": bool }
429 { "detail": "..." }
```

Server-side caps regardless of what the client sends: history truncated to the
last 6 messages, `question` length-limited. DRF `ScopedRateThrottle` (scope
`chat`) over Redis for per-IP limits, **plus a global daily counter** — a per-IP
throttle alone does not protect the endpoint from distributed abuse.

That global cap should be set **below the Gemini free-tier daily quota**, so the
system refuses politely with its own 429 instead of collapsing into upstream
quota errors it can't explain to the user.

- **New dependencies:** `django`, `djangorestframework`, `django-cors-headers`
  (Vercel preview URLs are dynamic → `CORS_ALLOWED_ORIGIN_REGEXES`), `django-redis`,
  `psycopg[binary]`, `pgvector`, `langgraph`, `google-genai`, `gunicorn`,
  `pyyaml`, `python-dotenv`.
- **One API account:** Google AI Studio. That is the only key in the system.

**Verify:** run the secrets checks in the Secrets section first. Then
`docker compose up` brings up web + db + redis; `manage.py migrate` then
`ingest_content` populates chunks (`select count(*) from chat_contentchunk`).
`curl` the endpoint three ways — an in-scope question returns an answer with
non-empty `sources`; "what's the weather in Riyadh" returns `refused: true`; a
follow-up sent with history resolves against the right record. `pytest` covers the
chunker, the ID-validation refusal path, and the throttle. Hammer the endpoint to
confirm a 429.

---

### Branch 4 — `feat/chat-ui`

New client component `frontend/components/sections/ask.tsx` plus
`frontend/lib/chat-api.ts`, placed on the page as another labelled section on the
existing `md:grid-cols-[7.5rem_1fr]` label grid — the mono `Ask` label in the left
column, matching `about.tsx` and `contact.tsx` exactly.

**The interaction ties into the join that already exists.** An answer's `sources`
are `record_id`s — the same keys `work.tsx` already filters on. Citing a record
lights that row in `--match` amber, which is not a new use of the token: it is the
same meaning it already carries ("this record is relevant right now"), reached
from a question instead of a hover. Requires lifting the join state that
`work.tsx` currently owns, or a small shared client context.

The only environment variable the frontend gets is `NEXT_PUBLIC_CHAT_API_URL` — a
URL, safe to publish. The section renders **only when that variable is set**, so
the production Vercel site is unchanged by this branch until a backend actually
exists to talk to (D6).

Constraints to respect: no new fonts or colors; motion stays within the page's
three existing moments and honors `prefers-reduced-motion`; the pending state
needs a real `aria-live` region, not just a spinner.

**Verify:** `npm run dev` with the env var set against the local compose stack —
ask an in-scope question and confirm the cited work rows light up; ask an
off-scope one and confirm the refusal reads as intended. Build with the var unset
and confirm the section is absent from `out/`. Grep `out/` for the Gemini key
value and confirm nothing. Keyboard-only pass through the input and results; check
reduced-motion.

---

## Open items, deliberately deferred

- **Production deploy** (VPS, domain, Caddy/TLS) — its own branch later (D6).
- **Guardrail / injection-detection node** — not built preemptively, per the
  original brief. The structured relevance gate covers the obvious cases.
- **`condense` and `relevance` could be one model call** returning
  `{standalone_question, in_scope, reason}` — halves latency and quota use on
  follow-up turns. Kept separate here because the graph structure is the point of
  the exercise; worth revisiting if the free-tier rate limit starts to bite.
- **Free-tier quotas are a real constraint**, not a footnote: they cap requests per
  minute and per day. Confirm the current limits when provisioning the key, and
  size the global daily counter against them.
