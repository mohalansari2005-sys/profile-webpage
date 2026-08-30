# backend

Django + DRF service behind the site's chat feature. Answers only from the
markdown corpus in `content/`, and refuses anything it cannot ground.

## Run it

    cp backend/.env.example backend/.env    # then fill in the real values
    npm run content                          # regenerates backend/corpus.json
    docker compose up -d --build
    docker compose run --rm web python manage.py migrate
    docker compose run --rm web python manage.py ingest_content

    curl -X POST localhost:8000/api/chat/ -H 'Content-Type: application/json' \
      -d '{"question":"What did he build at Majara?"}'

**After changing `backend/.env`, recreate the container — do not restart it.**
`docker compose restart` reuses the existing environment and will silently keep
the old value:

    docker compose up -d --force-recreate web

## Tests

    docker compose run --rm web pytest

Every test stubs the Gemini calls, so the suite needs no API key and spends no
quota.

## How it fits together

`corpus.json` is generated from `content/` by the same Node loader that
generates the site's `frontend/lib/content.ts`, so the bot and the page can
never disagree about what the corpus says. `ingest_content` chunks each record
(summary + one chunk per `##` section), embeds the changed ones, and deletes
orphans — re-running costs nothing when the corpus has not moved.

A request runs through `condense → relevance → retrieve → generate → log`.
Grounding is enforced in Python: if the model cites a chunk id retrieval did
not return, or reports insufficient context, the answer is replaced with a
refusal before it leaves the server.

## Two models, deliberately

| Setting | Default | Used by |
|---|---|---|
| `GEMINI_MODEL` | `gemini-3.5-flash` | `generate` (~10s) |
| `GEMINI_FAST_MODEL` | `gemini-3.5-flash-lite` | `condense`, `relevance` (~0.7s) |

A follow-up turn makes all three calls; the split keeps that near 12s rather
than 31s. Never send a `thinking_config` — the fast models reject it with a 400.

Model names are not stable. `gemini-2.5-flash`, which this feature was designed
around, now returns 404 while still appearing in `models.list()`. **Listing a
model does not prove it works** — call it once before depending on it.

## Secrets

`GEMINI_API_KEY` lives only in `backend/.env`, which is gitignored and listed in
`.dockerignore`. It is injected at runtime by compose and never appears in an
image layer, the compose file, or a log line.

**Never paste a real key into `.env.example`** — that file is committed.

Verify with exit codes, not output:

    git check-ignore -q backend/.env          # 0 = ignored, correct
    git check-ignore -q backend/.env.example  # 1 = committable, correct
    docker run --rm --entrypoint sh profile-webpage-web:latest -c 'printenv | grep -i gemini'

The last command must print nothing. Use plain `docker run`, not
`docker compose run` — compose always applies `env_file`, so it prints the
runtime key and proves nothing about the image.

`ChatLog` stores a salted SHA-256 of the client IP, never the address.

## Limits

`CHAT_RATE` is per IP; `CHAT_DAILY_CAP` is one counter for the whole service and
should sit below the Gemini free-tier daily quota, so the system refuses
politely instead of collapsing into upstream quota errors.
