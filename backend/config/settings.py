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
#
# OPENAI_FAST_MODEL (gpt-4.1-nano, $0.10 in / $0.40 out) serves the classifier
# calls, `condense` and `relevance`. gpt-5.4-nano is cheaper-looking but was
# rejected: on the relevance gate it returned in_scope=False for a plainly
# in-scope question on one trial and True on the next -- with a reason string
# arguing the question WAS in scope. relevance fails closed, so an unstable
# gate silently refuses real visitors. gpt-4.1-nano was 6/6 over two trials,
# including a prompt-injection attempt.
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_FAST_MODEL = os.environ.get("OPENAI_FAST_MODEL", "gpt-4.1-nano")
# text-embedding-3-small is natively 1536 dimensions, which is exactly the
# ContentChunk vector column -- no migration, and `dimensions` below is a
# no-op assertion rather than a Matryoshka truncation.
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIMENSIONS = 1536

IP_HASH_SALT = required("IP_HASH_SALT")
CHAT_DAILY_CAP = int(os.environ.get("CHAT_DAILY_CAP", "200"))
CORPUS_PATH = Path(os.environ.get("CORPUS_PATH", BASE_DIR / "corpus.json"))

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "chat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "chat"),
        "USER": os.environ.get("POSTGRES_USER", "chat"),
        "PASSWORD": required("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {"chat": os.environ.get("CHAT_RATE", "10/min")},
}

CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
