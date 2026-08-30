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

GEMINI_API_KEY = required("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
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
