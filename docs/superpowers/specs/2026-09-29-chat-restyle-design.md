# Chat restyle: bordered chat box with in-box auto-scroll

## Why
The chat rendered as a stack of table rows in the page: after an answer arrived the reader had to notice it and scroll. The goal is a conventional bordered chat window (questions right, answers left) built from ready-made components, that brings the new answer into view by itself.

## What
- **Component:** AI Elements `conversation` (Vercel's shadcn-registry chat component; wraps `use-stick-to-bottom`), installed with `shadcn add`. Its `message` component was **not** used: it pulls in `ai`, `streamdown` (markdown renderer with heavy transitive deps), tooltip and button-group, for plain-text answers.
- **New dependencies:** `use-stick-to-bottom` and `lucide-react` (conversation), `@base-ui/react` and `class-variance-authority` (the shadcn `base-nova` button the scroll-to-bottom control uses; `base-nova` is already the style in `components.json`). The CLI wrongly added a `cn` package and generated `button.tsx` importing from it; fixed to `@/lib/utils` and the package removed.
- **UI (`components/sections/ask.tsx`):** a fixed-height (`min(34rem, 70svh)`) bordered box; transcript scrolls inside it, the input bar is pinned to its bottom. Question bubbles use `ms-auto` (right in LTR), answer bubbles `me-auto`. Only tokens already in the palette (`card`, `secondary`, `background`, `rule`).
- **Direction:** the bubble's side follows the page direction; only the text inside carries `dir="auto"`, so an Arabic question renders RTL but stays on the question side (caught in real-Chrome QA: `dir` on the bubble flipped its `ms-auto`).
- **Auto-scroll:** StickToBottom keeps the newest content in view. When the newest turn is taller than the box, `KeepTurnInView` pins the top of that turn (question + first lines of answer) instead of its end. Only the box scrolls (`scrollTo` on the scroller; never `scrollIntoView`, which also moves the page). Respects `prefers-reduced-motion`.
- **Preserved:** turns/pending/failed/inFlight state, retry, `setCited` highlighting, source chips -> `scrollToRecord`, focus return to the input, `NEXT_PUBLIC_CHAT_API_URL` gate, seed prompts, `aria-busy` / log role.
- **Dropped:** the `Q.01` row labels (not a chat convention).

## Tests
`e2e/chat.spec.ts` (chat API mocked): sides, box scrolls but page doesn't, long answer keeps its start in view, Arabic text `dir=auto` + RTL, Arabic question stays on the question side, source chip focuses its record.
