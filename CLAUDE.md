# CLAUDE.md
 
Working conventions for this repo. Apply these to every task, not just the AI chat
feature — they reflect how I want to work generally, not one-off instructions.
 
## How to work with me
 
- I want an interactive workflow, not autonomous execution. Explain what you're about to
  change and why *before* changing it, especially for anything touching multiple files or
  architecture.
- IMPORTANT: If anything is unclear or ambiguous, ASK ME. Do not guess at what I meant or
  fill gaps with assumptions — I would rather answer a question than review a change based
  on a wrong assumption.
- Inspect existing patterns/conventions in the repo before creating something new. Match
  what's already here rather than introducing a parallel convention.
- Make the smallest reasonable change for the task at hand. Don't touch unrelated files.
- Do not claim something works unless it's actually been verified (tests run, endpoint
  hit, etc.) — tell me how to verify it myself.
## Branching
 
- One branch per unit of work (a "tier," a bug fix, a feature). Do not merge to `main`
  until I've reviewed the diff and explicitly confirmed.
- If a branch's work goes sideways or blows its time budget, it gets discarded — `main`
  should never see broken or half-finished work.
## After any meaningful change
 
Tell me:
- What changed and which files, with their responsibilities.
- Why it changed this way (not just that it works).
- How the feature/fix works end-to-end.
- What I should pay attention to or test myself.
## Engineering principles for this repo
 
- Prefer simple solutions; requirements should justify infrastructure, not the other way
  around — with one standing exception: the AI chat feature is a deliberate learning
  exercise where I chose heavier architecture (RAG, agent orchestration, self-hosted
  ops) on purpose, documented in `portfolio-ai-chat-prompts-v2.md`. Don't apply that
  same "keep it minimal" instinct to that feature's own scope — the complexity there is
  intentional, not a mistake to correct.
- Do not add a new framework, service, or dependency without telling me why it's needed
  first.
- Reuse existing patterns (content file structure, styling tokens, etc.) rather than
  inventing new ones.
## Stack reference
 
- Monorepo: `/frontend` (Next.js/TypeScript/Tailwind, deployed on Vercel) + `/backend`
  (Django/DRF, containerized, deployed on Hostinger via Docker Compose).
- Backend: Postgres (pgvector extension) for both vector storage and logging, Redis for
  rate limiting, LangGraph for the chat feature's agent logic, OpenAI for both
  generation and embeddings.
- Typography/palette (frontend): Source Serif 4 (body) / JetBrains Mono (labels) /
  display sans (headings); ink navy `#0F1626`, slate `rgb(92,103,121)`, base surface
  `#EBEEF3`, amber accent `#E09B2D`, green `#0B6E4F`. Don't introduce new fonts or colors
  without asking.
