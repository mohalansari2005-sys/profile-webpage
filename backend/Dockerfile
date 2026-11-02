FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"

COPY . .

# Not root: gunicorn is what the internet reaches through Caddy, and a hole in
# it should not come with the whole container. uid 1000 is usually the first
# user on a Linux host too, so the dev compose's ./backend bind mount stays
# writable for `docker compose run --rm web pytest`.
RUN useradd --create-home --uid 1000 app
USER app

# gthread workers, 2 processes x 4 threads: a turn spends most of its time
# waiting on OpenAI, and gunicorn's default -- one sync worker -- answered
# visitors strictly one at a time, so in a burst the seventh waited past the
# browser's 30s. Each turn's budget is a ContextVar and each thread has its own
# DB connection, so neither is shared between turns; the fast-model fallback is
# per process, so each worker pays one failed call. 8 connections at most, far
# under Postgres's default of 100.
# --timeout 120 was set because a turn's calls could outlast gunicorn's 30s
# default. Under gthread it only restarts a worker that stops responding, not a
# slow request: CHAT_TURN_BUDGET (25s) is what bounds a turn.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--worker-class", "gthread", "--workers", "2", "--threads", "4", "--timeout", "120"]
