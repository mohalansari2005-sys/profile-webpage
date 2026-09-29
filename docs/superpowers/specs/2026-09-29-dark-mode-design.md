# Dark mode

## Why
The site only had a light palette. Visitors on a dark OS get a bright page, and there is no way to choose.

## What
- **Tokens:** no new colors. The repo already carried a dormant `.dark` token block and the `.on-deep` palette; this activates that block. One adjustment: in dark, `--surface-deep` is `#151d31` (an existing hex) instead of the base navy, so the Projects section stays distinct from the page. Measured contrast on base/raised: text 14.98/13.92, `dim` 4.86/4.51, `match-ink` 5.92/5.50, `signal` 7.71/7.16.
- **No-flash:** an inline script in `<head>` (`app/layout.tsx`) sets `.dark` / `.light` on `<html>` from `localStorage.theme`, falling back to `prefers-color-scheme`, before first paint. `suppressHydrationWarning` on `<html>`. No `next-themes`.
- **No-JS:** the same tokens sit under `@media (prefers-color-scheme: dark) { :root:not(.light) }`, so visitors without script still follow the OS. `.light` (set only by an explicit light choice) wins over it.
- **Toggle:** `components/theme-toggle.tsx`, cycling System -> Light -> Dark, stored in `localStorage` (System = key absent). Uses `useSyncExternalStore` so the server render ("System") never mismatches; follows OS changes and other tabs live. Mounted in `components/top-bar.tsx`, absolutely positioned over the hero's top padding so it adds no layout.
- **Left alone:** `opengraph-image.tsx` (a rendered image, stays light).

## Tests
`frontend/e2e/theme.spec.ts`: OS-dark default, explicit light beats OS dark, Projects section distinct from page, script-blocked CSS fallback, toggle cycle + persistence across reload.

## Follow-up: cream text
The dark-mode ink was `#e7eaf0`, a bluish white that read as harsh. It is now `#e8e0cc` (warm cream, 13.73:1 on the base navy, 12.75:1 on raised). It is also the `.on-deep` foreground, so the Projects section text is cream in light mode too.
