# Chat restyle: bordered chat box with in-box auto-scroll

## Why
The chat rendered as a stack of table rows in the page: after an answer arrived the reader had to notice it and scroll. The goal is a conventional bordered chat window (questions right, answers left) built from ready-made components, that brings the new answer into view by itself.

## What
- **Components (all from AI Elements / shadcn registry, not hand-built):** `Conversation` (stick-to-bottom scrolling), `Message` + `MessageContent` (user bubble right, assistant text left), `Suggestions`/`Suggestion` (pill chips for the seed questions), and the shadcn `Button` / `ScrollArea` they rely on. Installed with `shadcn add https://registry.ai-sdk.dev/<name>.json`.
- **Trimmed, deliberately:** the registry `message` pulls `streamdown` (markdown renderer), `ai`, tooltip and button-group, which added ~170 kB gzipped JS for answers that are plain text. Only `Message` and `MessageContent` are kept (header comment in the file says so); `ml-auto` became `ms-auto` so the user's side follows page direction. Net cost of the whole chat UI: ~+6 kB gz over the previous chat. `prompt-input` was not used (38 kB of source: attachments, command palette, model select) - the input is a plain pill field.
- **Dependencies added:** `use-stick-to-bottom`, `lucide-react` (icons), `@base-ui/react`, `class-variance-authority` (shadcn `base-nova` button; `base-nova` is already the style in `components.json`). The shadcn CLI also added an unrelated `cn` npm package and generated files importing from it; those imports were pointed back at `@/lib/utils` and the package removed.
- **Making it read as a chatbot:** a real heading ("Ask my AI assistant about my work."), an "AI chat" label, an intro line, a chat header inside the box (bot icon, "Mohammed's AI assistant", "AI chatbot - answers only from his portfolio"), an assistant greeting with the suggestion chips, and a circular send button in a pill input (`aria-label="Send question"`) instead of a tiny "Ask" word.
- **Rounder:** box `rounded-3xl`, user bubble `rounded-2xl` with a small tail corner, pill input/chips/source chips (`rounded-full`). Palette tokens only.
- **Box and scrolling:** fixed height `min(36rem, 72svh)`; the transcript scrolls inside it and the input bar is pinned. StickToBottom keeps the newest content in view; when the newest turn is taller than the box, `KeepTurnInView` pins the top of that turn (question + first lines of answer) instead of its end, using `scrollTo` on the scroller (never `scrollIntoView`, which also moves the page). It re-sticks when a question is sent and whenever a turn fits, so a short reply after a long one is not left out of view (found in review). Respects `prefers-reduced-motion`.
- **Direction:** the message's side follows the page direction; only the text inside carries `dir="auto"`, so an Arabic question renders RTL but stays on the question side (found in real-Chrome QA).
- **Preserved:** turns/pending/failed/inFlight state, retry, `setCited` highlighting, source chips -> `scrollToRecord`, focus return to the input, `NEXT_PUBLIC_CHAT_API_URL` gate, `aria-busy` / log role.
- **Dropped:** the `Q.01` row labels (not a chat convention).

## Tests
`e2e/chat.spec.ts` (chat API mocked): bubble sides, box scrolls but page doesn't, long answer keeps its start in view, Arabic text `dir=auto` + RTL, Arabic question stays on the question side, source chip focuses its record., short reply after a long one is brought into view.
