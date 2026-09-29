# This website as a project (card + chatbot knowledge)

## Why
The site should list itself: a project card with real details from the repo, and the chatbot able to answer "how was this website built?".

## What
- **Record:** `content/projects/profile-webpage.md` (`proj-profile-webpage`), `repo` = `github.com/mohalansari2005-sys/profile-webpage`, with Arabic card fields (`title_ar`, `org_ar`, `summary_ar`). The frontmatter feeds the card; the body (eight `##` sections: what it is, how the site is built, the content pipeline, the chatbot, guardrails and cost, testing and CI, deployment, languages/theme/accessibility, why it is built this way) becomes the chatbot's chunks via `npm run content` -> `backend/corpus.json`.
- **Sourcing:** every claim was checked against `README.md`, `backend/README.md`, `DEPLOYMENT.md`, `docs/superpowers/specs/`, `package.json`, `ci.yml`, `deploy-backend.yml` and the code. Two claims were softened where the evidence was weaker than the wording (motion "limited to three moments" -> "a few deliberate moments"; the Arabic retrieval bug's cause is described as a design lesson, not as a confirmed live failure). Volatile facts (test counts, versions beyond the major stack) are left out so the record does not go stale.
- **Tools:** 11 new tool ids in `content/tools.yml` (TypeScript, React, Next.js, Tailwind CSS, Django, OpenAI API, LangGraph, RAG, pgvector, Playwright, GitHub Actions), added to their groups; the tool strip and the join pick them up automatically.
- **Scope gate:** the relevance prompt now says the website and chatbot the visitor is using are Mohammed's project, so "how was this built?" is `mohammed`, not `general` (which would have been refused). 8 new live-eval cases (6 English, 2 Arabic) cover it.
- **README:** four statements that were no longer true were corrected (only two client components; no component library; chat "local-only"; chat off in production), and short Languages/theme and Testing/CI sections added, so the repo the card links to agrees with the card.

## Knowledge base update path
`backend/corpus.json` changes -> `deploy-backend.yml` runs on merge to `main` (it watches `backend/**`) -> rebuild, `migrate`, `ingest_content` embeds the new record's chunks. Arabic fields are stripped from the corpus (tested), so nothing Arabic is embedded.

## Tests
- Content: the loader validates the new record's tool ids; `content:check` proves the committed artifacts are current (37 tests).
- E2E: both project cards render with GitHub links; on a phone viewport the second card is off-screen, chevrons are live, and **citing the new project scrolls the rail sideways to it and focuses it** (the path the carousel PR could not test with one project).
- Backend: offline suite unchanged (123); the new evals need `pytest -m eval` and an API key.

## Not verified
Live retrieval quality of the new chunks and the eval results (no API key on the dev machine). After the backend redeploys, ask the chat: "How was this website built?", "How does the chatbot work?", "كيف بُني هذا الموقع؟".
