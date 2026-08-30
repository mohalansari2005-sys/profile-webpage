# content

Markdown corpus — the single source of truth for both the rendered site and
the chat bot's retrieval. Not yet populated; see
`docs/superpowers/specs/2026-08-29-ai-chat-design.md`, Branch 2.

Frontmatter carries the structured fields the page renders. The body carries
the long-form prose only the bot retrieves. `frontend/lib/content.ts` becomes
generated from this directory at build time.
