# CI on pull requests + committed Playwright suite

## Why
Vercel deploys `main`, so nothing should reach `main` unverified. Until now the repo had only a backend deploy workflow (`deploy-backend.yml`) and no PR checks. Every branch in the 2026-09 site-edits plan (Arabic chat, dark mode, chat restyle, projects carousel, EN/AR i18n) is gated by this workflow.

## What
`.github/workflows/ci.yml`, triggered on `pull_request`, three independent jobs:

| Job | Runs |
|---|---|
| `frontend` | `npm ci`, `npm run lint`, `npm run build`, Playwright (Chromium) against the static `out/` |
| `content` | root `npm ci`, `npm test` (content pipeline), `npm run content:check` |
| `backend` | offline `pytest` against pgvector Postgres + Redis service containers |

`deploy-backend.yml` is untouched.

## Playwright
- `@playwright/test` and `serve` (devDependencies in `frontend/`). `serve` hosts the static export, since `next start` doesn't support `output: "export"`.
- Chromium only.
- The build is given a dummy `NEXT_PUBLIC_CHAT_API_URL` so the Ask section renders, and specs intercept that URL with `page.route`. No backend and no OpenAI calls, so CI costs nothing.
- Starter specs (`frontend/e2e/smoke.spec.ts`): every section renders; a mocked chat round-trip shows the answer. Later branches add their own specs.

## Not included
- The `pytest -m eval` live-model tests stay manual (they spend real API calls).
- No deploy step, no required-check branch protection (Mohammed can enable that in GitHub settings once CI is proven green).
