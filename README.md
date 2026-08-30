# profile-webpage

Personal portfolio for Mohammed Alansari — a static site built with Next.js and
deployed on Vercel.

**Live:** https://profile-webpage-liart.vercel.app

The page is built around one idea: everything on it is a typed record. Roles and
projects are rows with fields, and the tool strip above them is a join —
hovering or focusing a tool highlights every record that used it and drops the
rest back. It answers the question a reader actually has, which is not "what does
he know?" but "where did he actually use it?"

## Repo layout

```
frontend/   Next.js app, static-exported, deployed on Vercel
backend/    Django + DRF service for the chat feature; runs locally via Docker Compose
content/    Markdown corpus; frontend/lib/content.ts is generated from it
docs/       Specs and implementation plans
scripts/    Repo-level tooling
```

Vercel's Root Directory is set to `frontend`. All `npm` commands below run
from inside `frontend/`.

## Stack

- **Next.js 16** (App Router) exported to static HTML/CSS/JS
- **TypeScript**
- **Tailwind CSS v4**
- **next/font** — Bricolage Grotesque (display), Source Serif 4 (body),
  JetBrains Mono (labels and data), self-hosted at build time

No UI component library, no animation library, no state management library.

## Commands

```bash
cd frontend
npm run dev     # dev server on http://localhost:3000
npm run build   # production build; writes the static site to frontend/out/
npm run lint    # ESLint (next/core-web-vitals + TypeScript)
```

`npm test` at the repo root runs the corpus and generator unit tests.
`npm run start` exists but isn't used here — see Deployment below.

The backend runs separately, from the repo root:

```bash
docker compose up -d --build                              # web + postgres/pgvector + redis
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py ingest_content
docker compose run --rm web pytest                        # no API key needed; calls are stubbed
```

## Architecture

### Static export is the central constraint

`frontend/next.config.ts` sets `output: "export"`, so `next build` pre-renders every route
to static files at build time. There is no Node or serverless runtime in
production — Vercel serves plain files.

This rules out, for anything added later:

- API routes and Route Handlers that read the request
- Server Actions, Middleware, cookie-based logic
- `rewrites`, `redirects` and `headers` in `frontend/next.config.ts`
- Dynamic routes without `generateStaticParams()` covering every path
- `next/image`'s default optimizer — there's no image server at runtime

Anything needing a backend (a contact form, say) has to call an external service
from the client rather than a local API route.

### Server Components by default

Everything under `frontend/app/` renders at build time and ships no JavaScript. Exactly
two files opt into the client:

- `frontend/components/sections/work.tsx` — holds the join's state
- `frontend/components/reveal.tsx` — needs DOM geometry and IntersectionObserver

Everything else — hero, about, contact — is server-rendered and ships zero JS.

### The corpus lives in `content/`, generated into `frontend/lib/content.ts`

The Markdown corpus in `content/` at the repo root is the source of truth
for both the rendered site and, later, the chat feature's retrieval. It sits
outside `frontend/` on purpose: Tailwind v4's automatic content scan sweeps
text files under the project root for candidate class names, so prose
tracked inside `frontend/` feeds stray strings into that scan and injects
dead utility classes into production CSS — this project was bitten by
exactly that.

Frontmatter carries the structured fields the page renders (title, org,
period, tools, summary). The body carries long-form prose that only the
chat feature retrieves. It is deliberately never emitted into `content.ts` —
it reaches the backend through `backend/corpus.json` instead, so prose never
ships to the browser.

`frontend/lib/content.ts` is **generated** from `content/` — records are
data, not markup, so editing content never means touching JSX, but it also
means the file itself must never be hand-edited. From the repo root:

```bash
npm run content         # regenerate both generated artifacts from content/
npm run content:check   # fail if either committed artifact is stale
```

The generator writes **two** artifacts from one validated load:

| Artifact | Consumer | Contains |
|---|---|---|
| `frontend/lib/content.ts` | the rendered page | frontmatter fields only |
| `backend/corpus.json` | the chat backend's ingestion | the same fields **plus each record's body prose** |

Both are committed. One loader (`scripts/lib/corpus.mjs`) validates the corpus
once and feeds both, so the page and the bot can never disagree about what a
record says. Nothing in Python parses markdown — that duplication is exactly the
drift this design avoids.

The generator is deliberately *not* wired up as a `prebuild` step: Vercel
clones the whole repo, so `content/` is present, but its Root Directory is
`frontend`, so it installs only `frontend/`'s dependencies — `gray-matter`
and `js-yaml` aren't available there. The committed `frontend/lib/content.ts`
is what actually deploys — regenerate it and commit the result whenever
`content/` changes.

The important detail carried over from before: every string in a record's
`tools` array must match a `Tool.id`. **That string is the join key** the
tool strip filters on, so add the tool before referencing it. A key that
matches nothing used to render nothing, silently — it's now a hard
validation error, naming the offending record and the unknown tool.

### Design tokens

The palette is defined once as custom properties in `frontend/app/globals.css` and mapped
to Tailwind utilities through v4's `@theme inline`. Three colours carry meaning:

| Token      | Role                                                      |
|------------|-----------------------------------------------------------|
| `--signal` | green; marks structure                                    |
| `--match`  | amber; marks a joined row, and appears nowhere else       |
| `--dim`    | secondary text, at 4.9:1 on the paper ground              |

Keeping `--match` reserved for the match state is what makes the interaction
read. Spending it on decoration would break it.

Tailwind v4 detects source files automatically — there is no `content: []` array
to maintain. That automatic scan sweeps text files under the project root for
candidate class names, so prose in a tracked markdown file inside `frontend/`
would feed into the production CSS. That's why prose files (this README,
`backend/README.md`) are kept outside `frontend/` — `frontend/AGENTS.md` is the
one exception, generated by `next dev` itself rather than hand-authored.

### Motion

Limited on purpose to three moments: the hero fields arriving, rows arriving on
scroll, and the 180ms join transition. All of it is disabled under
`prefers-reduced-motion`.

### One invariant worth preserving

`frontend/components/reveal.tsx` does **not** rely on IntersectionObserver alone, and
shouldn't be simplified to.

An observer only reports a *crossing*. An element jumped clean over — an anchor
click, a restored scroll position, any instant jump, which is what
`prefers-reduced-motion` users always get — goes from below the viewport to above
it without ever intersecting, and no callback fires at all. Because static export
ships those elements at `opacity: 0`, "no callback" means permanently invisible
content.

So it checks geometry synchronously on mount and reveals anything already at or
above the fold, independent of the observer, and the observer's oversized top
`rootMargin` covers jumps that happen later. A `<noscript>` rule in the layout
handles the JS-disabled case. All three parts are load-bearing.

## The chat backend

`POST /api/chat/` answers questions about my work using only the `content/`
corpus, and refuses anything it cannot ground. It is local-only for now — no
VPS, no domain, no TLS.

A request runs through a five-node LangGraph: `condense → relevance → retrieve
→ generate → log`. Retrieval is pgvector cosine distance over 1536-dimension
Gemini embeddings.

**Grounding is enforced in Python, not asked for in the prompt.** The generate
step returns schema-validated JSON naming the chunk ids it used; if that set is
not a subset of what retrieval actually returned, or the model reports
insufficient context, the answer is discarded and replaced with a refusal before
it leaves the server.

The API key never reaches the browser — that is the whole reason this service
exists rather than calling Gemini from the client. See `backend/README.md` for
how to run it, the two-model split, and the secrets checks.

## Deployment

Vercel is connected to this repository. Pushing to `main` triggers a production
build and redeploy automatically — nothing to run by hand.

## Notes

`frontend/AGENTS.md` is generated and rewritten by `next dev` itself, not by
hand. It's expected to reappear if deleted; commit it rather than fight it.

`frontend/public/*.svg` are unused `create-next-app` starter assets.
