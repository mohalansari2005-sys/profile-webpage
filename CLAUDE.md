# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- `npm run dev` — start the dev server (http://localhost:3000)
- `npm run build` — production build; with `output: 'export'` set, this also generates the static site into `out/`
- `npm run start` — serve the production build (not used for this project — see Deployment note below; useful only for local sanity-checking a server-mode build)
- `npm run lint` — run ESLint (`eslint-config-next` core-web-vitals + TypeScript rules)

There is no test script configured.

## Architecture

This is a static personal portfolio: Next.js (App Router) + TypeScript + Tailwind CSS v4, exported to static HTML/CSS/JS and deployed on Vercel via a GitHub-connected repo (`mohalansari2005-sys/profile-webpage`, `main` branch — push to `main` triggers an automatic Vercel rebuild/redeploy).

**Static export (`next.config.ts`: `output: 'export'`)** is the central architectural constraint. `next build` pre-renders every route to static files at build time instead of relying on a Node/serverless runtime. This rules out, for any code added to this project:
- API routes / Route Handlers that read the incoming request
- Server Actions, Middleware, cookies-based logic
- `rewrites`/`redirects`/`headers` in `next.config.ts`
- Dynamic routes without `generateStaticParams()` covering every path
- `next/image`'s default (server-based) optimizer — avoid `next/image` unless a custom `loader` is configured, since there is no image optimization server at runtime

Anything requiring server-side behavior (e.g. a contact form) needs to call an external service (e.g. Formspree) client-side rather than a local API route.

**Routing** follows standard App Router conventions under `app/`: a folder's `page.tsx` is its route, `layout.tsx` wraps it and any nested routes without re-rendering on navigation. Everything under `app/` is a Server Component (rendered at build time, ships no JS) unless the file starts with `'use client'`.

**Styling**: Tailwind v4, wired through `postcss.config.mjs` → `@tailwindcss/postcss` plugin, entry point `app/globals.css` (`@import "tailwindcss"`). Tailwind v4 auto-detects source files for class scanning — there is no `content: [...]` array to maintain in a config file.

**Fonts**: loaded via `next/font/google` in `app/layout.tsx` (Geist Sans/Mono), exposed as CSS variables (`--font-geist-sans`, `--font-geist-mono`) rather than imported per-component.

## Notes

@AGENTS.md

`AGENTS.md` above is auto-generated/rewritten by `next dev` itself (not by us) and flags that this project's Next.js version (16.x) may differ from an AI assistant's training data — check `node_modules/next/dist/docs/` for the installed version's actual docs before assuming API behavior, particularly anything to do with routing, config, or static export. It's expected to reappear if deleted; commit it rather than fight it.

`public/*.svg` (file/globe/next/vercel/window icons) are unused `create-next-app` starter assets, not yet cleaned up.
