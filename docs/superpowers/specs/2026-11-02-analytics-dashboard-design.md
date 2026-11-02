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
- Not stored when: the User-Agent is missing or looks automated (bot, crawl, spider, headless, lighthouse, preview, curl, wget, python, etc.); the `Origin` header is present and not an allowed CORS origin (same allow-list as the chat: `CORS_ORIGINS` plus the `*.vercel.app` regex); the body is not valid JSON or `path` is missing/not a string. Best-effort spam filtering, not security.
- Per-IP throttle, reusing the `client_ip`-based throttle the chat uses, rate from `VISIT_RATE` (default `60/min`). It does **not** touch the chat's global daily cap.
- `authentication_classes = []` and `permission_classes = []`: anonymous by design.

### 3. Dashboard — `GET /dashboard/`

- Server-rendered Django template, inline CSS + inline SVG charts. No JavaScript libraries, no CDN, no web fonts beyond names the OS may have.
- **Auth:** HTTP Basic, password from `DASHBOARD_PASSWORD` (username ignored), compared with `hmac.compare_digest`. Unset → the URL 404s (dashboard disabled, collection still runs). Wrong/missing → 401 with `WWW-Authenticate: Basic realm="dashboard"`. Throttled per IP (`DASHBOARD_RATE`, default `30/min`) to slow password guessing. `Cache-Control: no-store`, `X-Robots-Tag: noindex`.
- **Range:** `?days=7|30|90|365`, default 30. Days are bucketed in `DASHBOARD_TZ` (default `Asia/Riyadh`), zero-filled.
- **Shows:**
  - KPI tiles for the range: visitors (distinct `ip_hash`), page views, chatbot users (distinct `ChatLog.ip_hash`), questions asked, share of visitors who used the chat, share of questions refused.
  - **Service errors:** questions that failed because the AI provider was unavailable (`ChatLog.refusal_reason == "generation unavailable"`), as a KPI tile and a series on the chat chart, highlighted when non-zero. Why: on 2026-10-23 OpenAI shut down `gpt-4.1-nano`, the gate failed closed, and every visitor was told their question was off-topic for ten days without anyone noticing. This tile is what would have shown it.
  - All-time line: total visitors, page views, chatbot users, questions, first recorded day.
  - Daily chart: visitors and page views per day.
  - Daily chart: chatbot users and questions per day.
  - Breakdown tables: pages (`/` vs `/ar`), referrers, sources, countries, devices, browsers.
  - Latest 25 chatbot questions: time, question (truncated), answered / refused / service error (with the refusal reason), latency.
- **Look:** the site's own palette tokens from `frontend/app/globals.css` (paper `#EBEEF3`, ink `#0F1626`, dim `#5C6779`, rule `#D2D8E0`, signal green `#0B6E4F`, match amber `#E09B2D`) with the dark-mode values under `prefers-color-scheme: dark`. No new colours or fonts.

### 4. Frontend beacon

- `frontend/lib/visit.ts`: `VISIT_URL` derived from `NEXT_PUBLIC_CHAT_API_URL` (`new URL("/api/visit/", CHAT_API_URL)`), so there is no second env var to configure: page views go to the same backend the chat uses, and nothing is sent when that URL is unset.
- `frontend/components/visit-beacon.tsx`: a client component rendered once per page (both locales). On mount it sends one beacon with `location.pathname`, `document.referrer` and `utm_source`/`ref`. Uses `navigator.sendBeacon`; falls back to `fetch(..., {keepalive: true, mode: "no-cors"})`. Never throws, never logs.
- **Owner opt-out:** visiting any page with `?analytics=off` stores a flag in `localStorage` and stops beacons from that browser; `?analytics=on` clears it. Storage errors are swallowed.

## Definitions and caveats (shown on the dashboard footer)

- A "visitor" is a distinct salted IP hash. People sharing an IP (office, mobile carrier NAT) count once; one person on two networks counts twice. Same definition the chat logs already use.
- Only browsers that run JavaScript are counted, which excludes most bots; visitors using strict ad/tracker blockers may also be missed.
- Data starts on the day this ships; there is no history before it.

## Configuration

New optional env vars in `backend/.env` (documented in `.env.example`, `DEPLOYMENT.md`, `backend/README.md`): `DASHBOARD_PASSWORD`, `DASHBOARD_TZ`, `VISIT_RATE`, `DASHBOARD_RATE`. The deploy workflow already runs `migrate`, so the new table is created on deploy.

## Tests

- Backend (`backend/tests/test_visit.py`, `test_dashboard.py`): stores a row with a hashed IP and normalised path; ignores bots, foreign origins, bad JSON; internal referrer becomes blank; 204 contract; throttling; dashboard 404 when unset, 401 without/with wrong password, 200 with the right one; distinct counts, timezone bucketing at a day boundary, zero-filling, chat metrics from `ChatLog`.
- Frontend e2e: the beacon fires once to `http://chat.test/api/visit/` with the right path on `/` and `/ar`; does not fire after `?analytics=off`; resumes after `?analytics=on`.
