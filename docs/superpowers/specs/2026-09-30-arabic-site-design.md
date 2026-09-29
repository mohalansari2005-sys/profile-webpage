# Arabic site: English at `/`, Arabic at `/ar`

## Decision that differs from the original plan
The plan said `/en` and `/ar`. Static export rules that out safely: `next.config` redirects are unsupported, and Vercel previews are login-protected, so a `/` -> `/en` redirect could not be verified before merge, and `/` is the live URL. **English stays at `/`** (canonical, OG image path, links, and every existing test unchanged); Arabic is `/ar`. Both are prerendered, shareable, and set `lang`/`dir` in the first byte of HTML. No dynamic segment, so no `generateStaticParams`, `dynamicParams` or `next/root-params` (which only works in Server Components anyway).

## Structure
- **Two root layouts** via route groups: `app/(en)/layout.tsx` and `app/(ar)/layout.tsx`, both rendering one shared `SiteLayout` (`<html lang dir>`, fonts, body) and `SiteHead` (theme no-flash script, `<noscript>` reveal fallback), so the two cannot drift. `/` is `app/(en)/page.tsx`, `/ar` is `app/(ar)/ar/page.tsx`; both render `HomePage({ locale })`. Spike-verified: `out/index.html` has `lang="en"`, `out/ar.html` has `lang="ar" dir="rtl"`, and a 404 page is still emitted (Next's default one; the site-styled 404 is gone, and `global-not-found` is experimental).
- **OG image:** `app/opengraph-image.tsx` stays at the app root (stable `/opengraph-image`). With no single root layout it no longer attaches itself, so `lib/site-metadata.ts` references it explicitly for both languages, with `hreflang` alternates (`en`, `ar`, `x-default`) and per-locale title/description.
- **Language toggle:** a plain `<a>` (crossing root layouts is a full navigation), carrying the `#section`. It stores the choice in `localStorage.lang`; an inline script on the English page sends a reader who chose Arabic to `/ar` when they open `/`. First-time visitors are never redirected.

## Strings
- No i18n library. `messages/en.ts` is the source; `messages/ar.ts` is typed `Messages` (= `typeof en`), so a missing key fails `tsc`. Placeholders (`{tool}`) are filled by `format()`; messages are plain data so they cross from server to client components.
- Server sections (Hero, About, Contact) take their slice as a `t` prop; client ones (Work, Ask, toggles) read `useI18n()` from `I18nProvider`.
- `lib/chat-api.ts` now returns error *kinds*; the UI maps them to copy in the page's language.
- Chat source chips show the record's title in the page's language (falls back to the server's English title for records without a row, i.e. the bio and FAQ).

## Content
Optional `title_ar`/`org_ar`/`period_ar`/`summary_ar` frontmatter -> `ar` on the record in `frontend/lib/content.ts` only. `renderCorpusJson` strips it, so **Arabic never reaches `backend/corpus.json`** (tested), and nothing is re-embedded. Any Arabic field left blank falls back to English.

## Type and layout
- IBM Plex Sans Arabic (approved) via `lib/font-arabic.ts`, imported only by the `/ar` layout (verified: absent from `index.html`). `html[lang=ar]` swaps `--font-display`/`--font-body`; mono labels keep JetBrains for Latin and fall back to Plex for Arabic glyphs.
- RTL CSS was landed separately in PR #15.

## Tests
`e2e/i18n.spec.ts` (15): `lang`/`dir` in raw HTML; every section Arabic; no horizontal overflow; Arabic typeface on `/ar` and not on `/`; translated records, Arabic project link label; Arabic theme toggle; `hreflang` + `og:image`; chat sides mirrored; Arabic source-chip titles; Arabic error text (and English unchanged); toggle round trip; `#hash` kept; remembered Arabic; no redirect for first-time visitors. Pipeline: `ar` emitted to the module, absent from `corpus.json`, validated (37 node tests).

## For the owner to proofread
All Arabic copy is drafted by Claude: `frontend/messages/ar.ts` and the `*_ar` fields in `content/experience/*.md` and `content/projects/keyraa.md`. In particular the spelling of the name "محمد الأنصاري".
