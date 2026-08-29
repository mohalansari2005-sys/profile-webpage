# backend

Django + DRF service for the AI chat feature. Not yet implemented — see
`docs/superpowers/specs/2026-08-29-ai-chat-design.md`, Branch 3.

Intended to run via a `docker-compose.yml` at the repo root alongside Postgres
(pgvector) and Redis, once built. Secrets will live in `backend/.env`, which is
gitignored; `backend/.env.example` documents the variable names.
