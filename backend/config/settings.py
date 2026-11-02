import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def required(name: str) -> str:
    # .strip() because a value pasted into .env with a stray leading space is
    # sent verbatim and fails upstream with a confusing 400, not a clear error.
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy backend/.env.example to backend/.env and fill it in."
        )
    return value


SECRET_KEY = required("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

OPENAI_API_KEY = required("OPENAI_API_KEY")
# One provider again, generation and embeddings both. Groq was evaluated first
# and rejected: it has no embeddings endpoint, so it would have forced a second
# provider and a second key just to keep retrieval working.
#
# Two generation models, both confirmed against the live API on 2026-08-31 by
# running the real node prompts, not by reading a model list. Prices below are
# per 1M tokens and were current that day; re-check before assuming them.
#
# OPENAI_MODEL (gpt-4.1-mini, $0.40 in / $1.60 out) serves `generate`. gpt-4.1,
# gpt-5.4 and gpt-5.4-mini were measured on the same grounding cases -- all four
# correctly set sufficient=false on questions the corpus cannot answer and none
# invented a chunk id, so the choice came down to price: at ~550 in / ~80 out
# per question and the 200/day CHAT_DAILY_CAP, this is ~$2.40/month worst case,
# against ~$12 for gpt-4.1 and ~$19 for gpt-5.4.
# Those per-question figures predate whole-record retrieval: generate now reads
# up to ~8k tokens of context and may write up to MAX_TOKENS_GENERATE
# (chat/openai_client.py). With the classifiers, the worst case is about a cent
# a turn -- ~$2 a *day* at the cap, not a month. The ranking by price stands;
# size CHAT_DAILY_CAP from ChatLog's real token counts.
#
# OPENAI_FAST_MODEL serves the classifier calls, `condense` and `relevance`. It
# was gpt-4.1-nano ($0.10 in / $0.40 out), 6/6 over two trials including a
# prompt-injection attempt, until OpenAI shut that model down on 2026-10-23:
# every gate call then failed and, failing closed, refused every visitor as
# off-topic. It is now gpt-4.1-mini, the model `generate` already runs, at ~4x
# nano's price. The gate is ~600 tokens in; condense runs only on follow-ups
# and Arabic, up to ~3.5k with a full history. If every one of the 200/day
# capped questions were a long follow-up that is ~$8/month more; a first-turn
# English question costs ~$0.0002 more. gpt-5.4-nano is cheaper-looking but was
# rejected: on the relevance gate it returned in_scope=False for a plainly
# in-scope question on one trial and True on the next -- with a reason string
# arguing the question WAS in scope. relevance fails closed, so an unstable
# gate silently refuses real visitors. If this model is ever not found again,
# openai_client falls back to OPENAI_MODEL rather than refusing everyone.
# A reasoning model counts its reasoning against the output caps, which are
# sized for this one: see MAX_TOKENS_* in chat/openai_client.py before switching.
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_FAST_MODEL = os.environ.get("OPENAI_FAST_MODEL", "gpt-4.1-mini")
# text-embedding-3-small is natively 1536 dimensions, which is exactly the
# ContentChunk vector column -- no migration, and `dimensions` below is a
# no-op assertion rather than a Matryoshka truncation.
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIMENSIONS = 1536

IP_HASH_SALT = required("IP_HASH_SALT")
CHAT_DAILY_CAP = int(os.environ.get("CHAT_DAILY_CAP", "200"))
# Seconds one chat turn may spend on OpenAI calls, under the browser's 30s
# (frontend/lib/chat-api.ts) so the visitor sees an answer or the 503.
CHAT_TURN_BUDGET = float(os.environ.get("CHAT_TURN_BUDGET", "25"))
CORPUS_PATH = Path(os.environ.get("CORPUS_PATH", BASE_DIR / "corpus.json"))

# Analytics. Collection always runs; the dashboard only exists once a password
# is set -- unset, /dashboard/ is a plain 404. .strip() for the reason given
# in required() above.
DASHBOARD_PASSWORD = (os.environ.get("DASHBOARD_PASSWORD") or "").strip()
# Days on the dashboard are calendar days here, not in UTC: a visit at 01:00
# Riyadh time belongs to that morning, not the previous evening.
DASHBOARD_TZ = os.environ.get("DASHBOARD_TZ", "Asia/Riyadh")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "chat",
    "analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

# Only the dashboard renders a template. APP_DIRS finds analytics/templates/;
# no context processors, because the page needs nothing but its own context.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "chat"),
        "USER": os.environ.get("POSTGRES_USER", "chat"),
        "PASSWORD": required("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        # Under gthread, gunicorn's --timeout no longer ends a stuck request,
        # and CHAT_TURN_BUDGET bounds only the OpenAI calls: a query waiting
        # on a lock would hold its thread -- one of 8 -- for good. Milliseconds.
        # Every query here is small -- a vector search over a few dozen chunks,
        # one ChatLog insert a turn, and migrate's and ingest_content's work on
        # the same tables -- so 15s is room for anything legitimate. A
        # migration that cannot get its lock in 5s fails rather than queue
        # every ChatLog write behind it, and can simply be run again.
        # connect_timeout (seconds) covers the one wait those two cannot: opening
        # a connection to a Postgres that does not answer.
        "OPTIONS": {"connect_timeout": 5,
                    "options": "-c statement_timeout=15000 -c lock_timeout=5000"},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        # Seconds. Every chat POST counts in Redis before anything else, so a
        # Redis that stops answering would otherwise hang every thread on it;
        # with these the request fails with a 500 instead.
        "OPTIONS": {"SOCKET_CONNECT_TIMEOUT": 2, "SOCKET_TIMEOUT": 3},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "chat": os.environ.get("CHAT_RATE", "10/min"),
        # A page load sends one beacon, so this only stops scripted floods.
        "visit": os.environ.get("VISIT_RATE", "60/min"),
        # Every dashboard request counts, right password or wrong, so this is
        # what slows a password guesser down.
        "dashboard": os.environ.get("DASHBOARD_RATE", "30/min"),
    },
    # JSON only. With TEMPLATES configured, DRF's default list would also
    # switch on the browsable API: an HTML form at /api/chat/ for anyone who
    # opens it in a browser.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]

# Without this, DEBUG=0 hands Django's request errors to mail_admins (no ADMINS
# are set) and nothing else, so a 500 or a failing OpenAI call left no trace.
# Everything at WARNING and up goes to stderr: `docker compose logs web`.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    # django.request logs every 4xx as a WARNING -- each throttled request and
    # each bot probing /wp-login.php. Only 5xx are worth a line.
    "loggers": {"django.request": {"level": "ERROR"}},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
# The local day, for the daily cap: it resets at midnight in Riyadh. Unset,
# Django's default America/Chicago rolled it over at 08:00-09:00 Riyadh time.
# Timestamps are still stored in UTC (USE_TZ).
TIME_ZONE = "Asia/Riyadh"
