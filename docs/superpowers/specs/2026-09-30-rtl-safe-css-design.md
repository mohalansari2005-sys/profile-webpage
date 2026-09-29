# RTL-safe CSS (refactor, no visual change in LTR)

## Why
The Arabic site (next PR) mirrors the layout. Physical-direction CSS would not mirror, so this lands first as a no-op in LTR that the existing 19 e2e tests can vouch for.

## What
- `work.tsx`: match marker `-left-4 sm:-left-6` -> `-start-4 sm:-start-6`; tool strip `syncEdges` measures `Math.abs(scrollLeft)` (scrollLeft is negative in RTL, which previously made the strip think it was always at the start).
- `about.tsx`: quote rule `border-l-2 pl-6` -> `border-s-2 ps-6`.
- `globals.css`: `[dir=rtl] .rule-draw` draws from the right; `[dir=rtl] .tool-strip` fades swap sides ("end" is on the left); `:lang(ar)` removes `letter-spacing` from `.field-label` and `tracking-*` utilities, since spacing pulls Arabic's joined letters apart.
- Already direction-safe, checked: the two-column grids (`grid-cols-[7.5rem_1fr]` follow `dir`), chat bubbles (`ms-auto`/`me-auto`, `rounded-ee/es`), the project rail (`Math.abs` scroll, `rtl:rotate-180` chevrons), symmetric `-mx-6 px-6`.

## Tests
`e2e/rtl.spec.ts` flips the English page to `dir=rtl lang=ar` and asserts: no horizontal overflow; hero rule origin on the right; About quote rule on the right; row marker on the right edge; no label letter-spacing; tool-strip mask 90deg -> 270deg; project chevrons page toward negative `scrollLeft` and enable Previous (the RTL path the carousel review flagged as untested).
