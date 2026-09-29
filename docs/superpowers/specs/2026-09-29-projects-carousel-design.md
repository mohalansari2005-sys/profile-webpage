# Projects as a horizontal rail + GitHub link on every project

## Why
Projects were stacked rows, which becomes a long scroll as projects are added. Also, every project should link to its GitHub repo (standing rule).

## What
- **Rail:** `ProjectRail` / `ProjectCard` in `components/sections/work.tsx`. Projects sit side by side in a horizontal scroll-snap row of rounded, bordered cards (`w-[min(22rem,85vw)]`, `snap-start`); chevron buttons in the section header page by one card and disable at the ends (and when everything fits). No carousel library: plain `overflow-x-auto` + `scrollBy`, scrollbar hidden.
- **State:** cards reuse the existing `rowState` (lit on a tool/citation match, dimmed otherwise). The card border turns amber when lit, in place of the row's left-edge marker, which the rail's overflow would clip. `scrollToRecord` still works unchanged: `scrollIntoView` (default `inline: nearest`) also scrolls the rail sideways to a cited card.
- **Direction-aware:** `scrollLeft` is read as `Math.abs`, "previous" flips in RTL, chevron glyphs use `rtl:rotate-180`, so the rail is ready for the Arabic branch.
- **GitHub link:** new optional `repo` field, same pattern as the existing `href` (`scripts/lib/corpus.mjs` -> `build-content.mjs` -> `lib/content.ts` -> `backend/corpus.json`). `href` is left free for a future live-demo link. Keyraa's `repo` is `https://github.com/mohalansari2005-sys/keyraa-hotel-booking`. Rendered as a round GitHub-icon link on the card (`target=_blank rel="noopener noreferrer"`, `aria-label="<title> on GitHub"`). The build warns (not fails) when a project has no `repo`. The icon is a new `components/github-icon.tsx` (Simple Icons path, same as Contact); Contact still has its own inline copy, deliberately untouched here.
- **Experience** stays a stacked list (out of scope).

## Tests
- `scripts/`: `repo` emitted only when present, passed through the loader, rejected if not a string (32 tests).
- `e2e/projects.spec.ts`: repo link `href`/`target`/`rel`; rounded cards in an `overflow-x: auto` rail; chevrons disabled with one project; with extra cards (cloned in-page, since only one project exists) chevrons page the rail and disable at both ends; paging doesn't move the page.

## Not covered
Horizontal `scrollToRecord` to an off-screen card (needs a second real project) and RTL behaviour (Arabic branch).
