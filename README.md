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
backend/    Django + DRF service for the chat feature (not yet built)
content/    Markdown corpus feeding both the site and the bot (not yet built)
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

There is no test script. `npm run start` exists but isn't used here — see
Deployment below.

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

Everything under `app/` renders at build time and ships no JavaScript. Exactly
two files opt into the client:

- `frontend/components/sections/work.tsx` — holds the join's state
- `frontend/components/reveal.tsx` — needs DOM geometry and IntersectionObserver

Everything else — hero, about, contact — is server-rendered and ships zero JS.

### Content lives in `frontend/lib/content.ts`

Records are data, not markup, so editing the content never means touching JSX.

The important detail: every string in a record's `tools` array must match a
`Tool.id`. **That string is the join key** the tool strip filters on, so add the
tool before referencing it. A key that matches nothing renders nothing, silently.

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
to maintain.

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

## Deployment

Vercel is connected to this repository. Pushing to `main` triggers a production
build and redeploy automatically — nothing to run by hand.

## Notes

`frontend/AGENTS.md` is generated and rewritten by `next dev` itself, not by
hand. It's expected to reappear if deleted; commit it rather than fight it.

`frontend/public/*.svg` are unused `create-next-app` starter assets.
