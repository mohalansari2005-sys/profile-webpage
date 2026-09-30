# Phone and iPad layout

## Problem
On a phone the page looked misaligned. Measured with Playwright at 360-430px viewports: the document was **643px wide on a 390px screen** (519px on `/ar`), so the page panned sideways and content sat off-screen. The cause was one line of CSS: the section grids were `grid` with no explicit column below their breakpoint, so the single implicit column grew to fit its widest child, and in the chat that child was a no-wrap row of suggestion chips (`w-max`, `flex-nowrap`). iPad sizes (744, 820, 1024) did not overflow but were the desktop layout squeezed: 24px gutters on an 820px screen, and the section label column started at 768px while record rows used it from 640px, so at iPad mini's 744px the two disagreed.

## Device classes
| Class | Width | Layout |
|---|---|---|
| Phone | < 640px | Single column, 24px gutter, label above content |
| Tablet (iPad portrait / mini) | 640-1023px | Label column beside content, 40px gutter, taller chat |
| Desktop / iPad landscape | >= 1024px | Unchanged (24px gutter, 1024px column) |

## Changes
- **Overflow fix:** `grid-cols-1` (i.e. `minmax(0,1fr)`) on every section grid and row grid, so children shrink instead of stretching the page. The chat suggestions wrap inside the bubble (`flex-wrap`, `w-auto`, chips `h-auto whitespace-normal text-start`) instead of forcing a wide no-wrap row.
- **Gutter token:** `--gutter` (1.5rem / 2.5rem on tablets / 1.5rem) with two utilities in `globals.css`, `gutter` and `gutter-bleed` (for the tool strip and project rail, which run edge to edge but align to the column). Replaces the hard-coded `px-6` / `-mx-6` in the sections, top bar, strip and rail, so they cannot drift apart.
- **Tablet label column:** section grids switch to `[7.5rem_1fr]` at `sm` (640px) instead of `md` (768px), matching the record rows.
- **Pinned "Built with" bar (phone):** the label no longer wraps ("BUILT / WITH") and the hint truncates to one line instead of wrapping to two, so the always-visible bar is shorter.
- **Touch targets:** `pointer-coarse:` variants raise the tool chips, Clear, project chevrons, card GitHub link, suggestion and source chips and the send button to finger-sized on touch screens (phones and iPads); mouse layouts are unchanged. (The icon toggles are already 44px on phones.)
- **Chat height:** `min(34rem,72svh)` on phones, `min(42rem,64svh)` on tablets (tall screens), `min(36rem,72svh)` on desktop.
- **Contact links** get `overflow-wrap: anywhere` so a long URL wraps instead of overflowing at 320px.

## Tests (`e2e/responsive.spec.ts`, 52 tests)
Eight sizes (320, 375, 390, 430, 744, 820, 834, 1024) x both languages: never wider than the screen; correct gutter (24 / 40 / 24); section label stacked on phones, beside content from 640px. Phone specifics: the pinned bar's label and hint are one line; the chat box fits the phone and its suggestions wrap inside it. Under touch emulation (`isMobile`, so `pointer: coarse`): toggles, chevrons >= 44px, tool chips >= 38px. Chat is taller on an iPad than on a phone or laptop. **Checked against the unfixed code: 20 of these fail there** (every phone overflow case, the iPad gutters and label column), so they guard the fix.

## Not covered
Real devices and the Vercel preview (login-protected); Safari/WebKit-specific quirks (tests run in Chromium with device emulation); landscape phones.
