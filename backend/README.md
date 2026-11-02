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

Every test stubs the OpenAI calls, so the suite needs no API key and spends no
money.

    docker compose run --rm web pytest -m eval

The `eval` cases are the exception, and are deselected above by default. They
call the real `OPENAI_FAST_MODEL` to check what the stubs cannot: whether the
prompts *judge* correctly. A full run is ~30 gpt-4.1-mini calls, about a cent.

They exist because a scope gate that refused "What is Majara?" -- naming his own
employer as unrelated to him -- passed a fully green suite. Every other test
stubs `structured`, so all of them proved the wiring and none of them read the
prompt. Run these after editing any prompt.

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

## One provider, two models

OpenAI serves both halves: generation and embeddings. Groq was evaluated first,
for its free tier, and rejected — it has no embeddings endpoint, so it would
have forced a second provider and a second key just to keep retrieval working.

| Setting | Default | Used by |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4.1-mini` | `generate` |
| `OPENAI_FAST_MODEL` | `gpt-4.1-mini` | `condense`, `relevance` |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | `retrieve`, `ingest_content` |

`text-embedding-3-small` is natively 1536-dimensional, which is exactly the
`ContentChunk` vector column, so `dimensions=1536` asserts the width rather than
truncating to it.

Changing `OPENAI_EMBED_MODEL` invalidates every stored vector: embeddings from
two different models are not comparable, and the chunk *text* is unchanged, so
the text hash alone cannot see it. `ingest_content` therefore stores a hash of
the text **and** the embedding model, so a model change re-embeds the whole
corpus on the next run. Without that, the old vectors survive and retrieval
degrades silently rather than failing.

Structured output goes through `chat.completions.parse`, which is handed the
Pydantic class itself and enforces the schema server-side.

**Catch more than `APIError`.** `LengthFinishReasonError` and
`ContentFilterFinishReasonError` subclass `OpenAIError`, *not* `APIError`, so an
`except APIError` alone lets a truncated or filtered response escape as a 500.
See `chat/openai_client.py` — both are caught and mapped to a refusal, without
the `api_error` flag, because they mean a bad response rather than an outage.

Model names are not stable. **Listing a model does not prove it works** — call
it once before depending on it, with the real node prompt rather than a toy one.
The Gemini setup this replaced was designed around `gemini-2.5-flash`, which
404s while still appearing in `models.list()`. On OpenAI the same lesson cost
less but showed up later: `gpt-5.4-nano` answers the relevance prompt fine, then
returns a different `in_scope` for the same in-scope question on a second trial.
`relevance` fails closed, so that reads to a visitor as a random refusal. It was
rejected for `OPENAI_FAST_MODEL` on those grounds — see `config/settings.py`.

`gpt-4.1-nano` held that slot until OpenAI shut it down on 2026-10-23. The gate
fails closed, so for ten days every question was refused as off-topic and
nothing said why. What now stops a repeat:

- The default is `gpt-4.1-mini`, and the env templates no longer pin model
  names, so a new default actually reaches the server.
- A fast model that comes back `model_not_found` makes `openai_client` fall back
  to `OPENAI_MODEL` for the life of that worker (an env file can still name a
  retired model).
- An outage -- auth, quota, rate limit, 5xx, a timeout (20s, one retry, so it
  ends inside gunicorn's 120s), a retired model with nowhere to fall back --
  answers **503**, the UI's "service hit an error, try again", instead of a
  refusal. It still counts against `CHAT_DAILY_CAP`: earlier calls in the turn
  may have been billed, and the cap is the hard spend limit.
- Only a prompt OpenAI rejects for what the visitor sent (`invalid_prompt`,
  `context_length_exceeded`) stays a refusal, logged `request rejected`. Any
  other 400 can be configuration, so it is an outage and gets noticed.
- Every OpenAI failure is logged to stderr (`docker compose logs web`) with its
  status and error code.
- `.github/workflows/chat-canary.yml` asks the live API one real question every
  day and after every backend deploy, and fails -- which emails the repo owner
  -- if it is refused or errors.

`refusal_reason` on an outage row says which call failed: `generation
unavailable` for the gate or `generate`, `retrieval unavailable` for the
embedding.

Check OpenAI's deprecations page before a model's shutdown date, not after.

## Secrets

`OPENAI_API_KEY` lives only in `backend/.env`, which is gitignored and listed in
`.dockerignore`. It is injected at runtime by compose and never appears in an
image layer, the compose file, or a log line.

**Never paste a real key into `.env.example`** — that file is committed.

Verify with exit codes, not output:

    git check-ignore -q backend/.env          # 0 = ignored, correct
    git check-ignore -q backend/.env.example  # 1 = committable, correct
    docker run --rm --entrypoint sh profile-webpage-web:latest -c 'printenv | grep -i openai'

The last command must print nothing. Use plain `docker run`, not
`docker compose run` — compose always applies `env_file`, so it prints the
runtime key and proves nothing about the image.

`ChatLog` stores a salted SHA-256 of the client IP, never the address.

## Limits

`CHAT_RATE` is per IP; `CHAT_DAILY_CAP` is one counter for the whole service.
It was sized against a free-tier daily quota. OpenAI is billed per token, not
capped, so this counter is now the **spend** limit — it is the only thing
between a scripted abuser and a real bill. Size it against what you are willing
to pay per day, not against a quota.

To read the spend, each `ChatLog` row's `prompt_tokens`/`completion_tokens`
belong to the model in its `model` column, and never mix two rates:

| Row | `model` | Tokens counted |
|---|---|---|
| Refused at the gate | the fast model that ran (`OPENAI_FAST_MODEL`, or `OPENAI_MODEL` after a fallback) | `condense` + `relevance`, summed |
| `retrieval unavailable` | the fast model that ran | `condense` + `relevance`, summed |
| Answered, or refused by `generate` | `OPENAI_MODEL` | the `generate` call only |

So an answered turn does not record the two fast calls that preceded it. That
undercount dates from when the fast model was nano: one row names one model,
and adding nano tokens to a mini row at mini's rate would have overstated the
bill. Multiply each row by its own model's price and sum — do not sum the
token columns across rows and multiply once.
