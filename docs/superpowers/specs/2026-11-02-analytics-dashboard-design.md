# Analytics dashboard — design

**Date:** 2026-11-02
**Branch:** `feat/analytics`
**Asked for:** "how many visitors, history of visits, also how many people used the chatbot" — an easy dashboard.
**Decision (owner, 2026-11-02):** self-hosted in the existing Django backend. No Vercel Analytics, no third-party service.

## Why this shape

The backend already has Postgres, a salted IP hash (`chat.models.hash_ip`) and a `ChatLog` row per question. Chatbot usage is therefore already recorded; only page views are missing. Adding one table, one beacon endpoint and one server-rendered page answers all three questions with no new service, no new Python or npm dependency, no cookies and no third party seeing visitors.

Vercel Web Analytics was rejected: it is a new dependency, lives in a dashboard the owner must enable, and cannot count chatbot use on the free plan.

## Pieces

### 1. `PageView` model (new Django app `analytics`)

| field | type | notes |
|---|---|---|
| `created_at` | DateTime, `auto_now_add`, indexed | |
| `ip_hash` | Char(64), indexed | `chat.models.hash_ip(client_ip(request))` — the **same key** `ChatLog.ip_hash` uses, so "visitors who used the chat" is a join. A raw IP never reaches the DB. |
| `path` | Char(200) | normalised: leading `/`, no trailing slash except root, no query/hash. |
| `referrer_host` | Char(200), blank | host of `document.referrer`; blank when direct or when it is the site's own host (internal navigation such as the language toggle). |
| `source` | Char(100), blank | `utm_source` / `ref` query param if the visitor arrived with one. |
| `country` | Char(2), blank | `CF-IPCountry` header if Cloudflare is in front (DEPLOYMENT.md allows proxied DNS); blank otherwise. No GeoIP database. |
| `device` | Char(10) | `mobile` / `tablet` / `desktop`, derived from the User-Agent. |
| `browser` | Char(20) | coarse family (Chrome, Safari, Firefox, Edge, Samsung, Other). The UA string itself is not stored. |

### 2. Beacon endpoint — `POST /api/visit/`

- Body is JSON sent as `text/plain` (so `navigator.sendBeacon` needs no CORS preflight): `{"path": "/ar", "referrer": "https://www.linkedin.com/...", "source": "linkedin"}`.
- Always answers **204** with an empty body, including for ignored requests, so nothing about filtering leaks. Throttled requests get 429 (DRF).
- Not stored when: the User-Agent is missing or looks automated (bot, crawl, spider, headless, lighthouse, preview, curl, wget, python, etc.); the `Origin` header is present and not exactly one of `CORS_ORIGINS` (the `*.vercel.app` regex the chat's CORS also allows is deliberately not accepted: preview deployments are QA, not visitors); the body fails `VisitSerializer` (JSON, parsed as `text/plain` or `application/json`; `path` a string, `referrer`/`source` optional strings, each at most 2000 characters, refused if it holds NUL or a lone surrogate: a bad `path` drops the beacon, a bad optional field counts as not sent). Best-effort spam filtering, not security.
- A dropped connection mid-body (`UnreadablePostError`) or a `DatabaseError` on save (the first deploy serves before `migrate`) is also a 204, with one WARNING log line and no traceback.
- Per-IP throttle, reusing the `client_ip`-based throttle the chat uses, rate from `VISIT_RATE` (default `60/min`). It does **not** touch the chat's global daily cap.
- `authentication_classes = []` and `permission_classes = []`: anonymous by design.

### 3. Dashboard — `GET /dashboard/`

- Server-rendered Django template, inline CSS + inline SVG charts. No JavaScript libraries, no CDN, no web fonts beyond names the OS may have.
- **Auth:** HTTP Basic, password from `DASHBOARD_PASSWORD` (username ignored), compared with `hmac.compare_digest`. Unset → the URL 404s (dashboard disabled, collection still runs). Wrong/missing → 401 with `WWW-Authenticate: Basic realm="dashboard"`. Throttled per IP (`DASHBOARD_RATE`, default `30/min`) to slow password guessing. `Cache-Control: no-store`, `X-Robots-Tag: noindex`.
- **Range:** `?days=7|30|90|365`, default 30. Days are bucketed in `DASHBOARD_TZ` (default `Asia/Riyadh`), zero-filled.
- **Shows:**
  - KPI tiles for the range: visitors (distinct `ip_hash`), page views, chatbot users (distinct `ChatLog.ip_hash`), questions asked, share of visitors who used the chat, share of questions refused.
  - **Service errors:** questions that failed because the AI provider was unavailable (`ChatLog.unavailable`, set by the chat's log node from the graph's `unavailable`; migration `chat.0002` backfilled it for rows whose `refusal_reason` is exactly `generation unavailable`, `retrieval unavailable` or `condense unavailable`), as a KPI tile and a series on the chat chart, highlighted when non-zero. Not counted as refusals. Why: on 2026-10-23 OpenAI shut down `gpt-4.1-nano`, the gate failed closed, and every visitor was told their question was off-topic for ten days without anyone noticing. This tile is what would have shown it.
  - **Synthetic questions are left out** of every chat number, chart and the latest list: `ChatLog.synthetic`, set by the chat view when the request has no `Origin` (the daily canary, curl checks) or one not exactly in `CORS_ORIGINS` (Vercel previews). The chat still answers them. Said in the footer.
  - All-time line: total visitors, page views, chatbot users, questions, first recorded day.
  - Daily chart: visitors and page views per day.
  - Daily chart: chatbot users and questions per day.
  - Breakdown tables: pages (`/` vs `/ar`), referrers, sources, countries, devices, browsers.
  - Latest 25 chatbot questions: time, question (truncated), answered / refused / service error (with the refusal reason), latency.
- **Look:** the site's own palette tokens from `frontend/app/globals.css` (paper `#EBEEF3`, ink `#0F1626`, dim `#5C6779`, rule `#D2D8E0`, signal green `#0B6E4F`, match amber `#E09B2D`) with the dark-mode values under `prefers-color-scheme: dark`. No new colours or fonts.

### 4. Frontend beacon

- `frontend/lib/visit.ts`: `VISIT_URL` derived from `NEXT_PUBLIC_CHAT_API_URL` (`new URL("/api/visit/", CHAT_API_URL)`), so there is no second env var to configure: page views go to the same backend the chat uses, and nothing is sent when that URL is unset.
- `frontend/components/visit-beacon.tsx`: a client component rendered once per page (both locales). On mount it sends one beacon with `location.pathname`, `document.referrer` and `utm_source`/`ref`. Uses `navigator.sendBeacon`; falls back to `fetch(..., {keepalive: true, mode: "no-cors"})`. Never throws, never logs.
- **Redirected `/`:** the head script in `site-head.tsx` that sends a returning Arabic reader from `/` to `/ar` first sets `data-redirecting` on `<html>` (`REDIRECTING` in `lib/visit.ts`); the beacon sends nothing from a page carrying it, so `/ar` counts the visit once. The redirect, and the `?lang=en` clean-up on the English page, keep the rest of the query and the hash, so `utm_source` and `analytics=off` still reach the beacon.
- **Owner opt-out:** visiting any page with `?analytics=off` stores a flag in `localStorage` and stops beacons from that browser; `?analytics=on` clears it. Storage errors are swallowed.

## Definitions and caveats (shown on the dashboard footer)

- A "visitor" is a distinct salted IP hash. People sharing an IP (office, mobile carrier NAT) count once; one person on two networks counts twice. Same definition the chat logs already use.
- Only browsers that run JavaScript are counted, which excludes most bots; visitors using strict ad/tracker blockers may also be missed.
- Data starts on the day this ships; there is no history before it.
- Chat numbers count only questions from the live site; synthetic ones (canary, curl, previews) are left out. Rows logged before `ChatLog.synthetic` existed cannot be told apart and still count.

## Configuration

New optional env vars in `backend/.env` (documented in `.env.example`, `DEPLOYMENT.md`, `backend/README.md`): `DASHBOARD_PASSWORD`, `DASHBOARD_TZ`, `VISIT_RATE`, `DASHBOARD_RATE`. The deploy workflow already runs `migrate`, so the new table is created on deploy.

## Tests

- Backend (`backend/tests/test_visit.py`, `test_dashboard.py`): stores a row with a hashed IP and normalised path; ignores bots, foreign and preview origins, bad JSON, strings Postgres cannot store in `path`; internal referrer becomes blank; 204 contract, including a dropped connection and a database error (one WARNING, no traceback); throttling; dashboard 404 when unset, 401 without/with wrong password, 200 with the right one; distinct counts, timezone bucketing at a day boundary, zero-filling, chat metrics from `ChatLog`, service errors by `ChatLog.unavailable`, synthetic rows left out, shares `<1%`/`>99%`, a constant query count. Chat (`test_api.py`, `test_graph.py`, `test_models.py`): the synthetic rule per `Origin`, both flags reach the row, the `chat.0002` backfill matches the exact labels only.
- Frontend e2e: the beacon fires once to `http://chat.test/api/visit/` with the right path on `/` and `/ar`; does not fire after `?analytics=off`; resumes after `?analytics=on`; a returning Arabic reader opening `/` is counted once, for `/ar`; the head script marks `/` before redirecting and a marked page sends nothing; `?lang=en` keeps `utm_source`, `analytics=off` and the hash.
