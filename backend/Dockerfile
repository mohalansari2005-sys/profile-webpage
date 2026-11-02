FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app

# Not root: gunicorn is what the internet reaches through Caddy, and a hole in
# it should not come with the whole container. uid 1000 is usually the first
# user on a Linux host too, so the dev compose's ./backend bind mount stays
# writable for `docker compose run --rm web pytest`. Created before anything
# is copied, so a code change does not rebuild this layer.
RUN useradd --create-home --uid 1000 app

COPY pyproject.toml ./
# As root: pip installs into the system site-packages.
RUN pip install --no-cache-dir ".[dev]"

# COPY writes root-owned files whatever USER is, which is all the app needs:
# it only reads its code.
USER app
COPY . .

# gthread workers, 2 processes x 4 threads: a turn spends most of its time
# waiting on OpenAI, and gunicorn's default -- one sync worker -- answered
# visitors strictly one at a time, so in a burst the seventh waited past the
# browser's 30s. Each turn's budget is a ContextVar and each thread has its own
# DB connection, so neither is shared between turns; the fast-model fallback is
# per process, so each worker pays one failed call. 8 connections at most, far
# under Postgres's default of 100.
# 8 turns at once is a ceiling, not what a burst gets: each worker accepts more
# connections than it has threads and queues the rest itself, so one can hold
# twice the other's share while the other has threads idle. In a test, 24
# simultaneous turns took 5 rounds to answer, where an even 8-way split takes 3;
# 1 worker x 8 threads has no such imbalance. A queued turn's CHAT_TURN_BUDGET
# starts only when a thread picks it up, so the queueing comes on top of the
# 25s, against the browser's 30s.
# --timeout 120 was set because a turn's calls could outlast gunicorn's 30s
# default. Under gthread it only restarts a worker that stops responding, not a
# slow request, so nothing bounds a turn as a whole. Each wait in it is bounded
# instead: CHAT_TURN_BUDGET (25s) covers its OpenAI calls, statement_timeout
# and lock_timeout its queries, and socket timeouts its Redis calls
# (config/settings.py).
# --keep-alive 150 keeps an idle connection from Caddy open longer than Caddy
# keeps it (60s, the Caddyfile's transport keepalive), so Caddy is always the
# side that closes it. At gthread's default of 2s, gunicorn closed connections
# Caddy still meant to reuse, and a POST Caddy wrote into one as it closed was
# a 502. Only Caddy connects here, so the idle connections held are its pool.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--worker-class", "gthread", "--workers", "2", "--threads", "4", "--timeout", "120", \
     "--keep-alive", "150"]
