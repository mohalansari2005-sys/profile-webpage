# content

Markdown corpus — the single source of truth for both the rendered site and
the chat bot's retrieval. See
`docs/superpowers/specs/2026-08-29-ai-chat-design.md`, Branch 2.

Frontmatter carries the structured fields the page renders. The body carries
the long-form prose only the bot retrieves. `frontend/lib/content.ts` is
generated from this directory by an explicit `npm run content` step from the
repo root — it is deliberately not run as part of the build.
