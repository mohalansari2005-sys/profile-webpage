---
id: "proj-profile-webpage"
kind: "projects"
title: "Portfolio website with an AI chat"
org: "Personal project"
period: "2026"
repo: "https://github.com/mohalansari2005-sys/profile-webpage"
tools: ["typescript", "react", "nextjs", "tailwind", "python", "django", "langgraph", "openai-api", "rag", "postgres", "pgvector", "redis", "docker", "pytest", "playwright", "github-actions"]
summary: "This website: a statically exported Next.js and TypeScript front end whose content is a validated Markdown corpus, plus a Django and LangGraph chatbot that answers questions about my work by retrieving over pgvector with OpenAI models, and refuses anything it cannot ground in that corpus. English and Arabic (right-to-left), dark mode, CI with Playwright, and a backend that deploys itself to a VPS."
title_ar: "موقع المحفظة مع دردشة ذكية"
org_ar: "مشروع شخصي"
summary_ar: "هذا الموقع: واجهة Next.js وTypeScript مُصدَّرة بشكل ثابت، محتواها مجموعة Markdown موثَّقة، مع روبوت دردشة مبني على Django وLangGraph يجيب عن أسئلة حول أعمالي عبر الاسترجاع من pgvector ونماذج OpenAI، ويرفض أي سؤال لا يستطيع إسناده إلى هذه المجموعة. بالعربية والإنجليزية (من اليمين إلى اليسار)، ووضع داكن، وتكامل مستمر مع Playwright، وخلفية تنشر نفسها إلى خادم VPS."
---

## What it is

This project is the website you are on right now: my portfolio, built as a
small system rather than a template. The page is a set of typed records (roles
and projects with a title, an organisation, a period, a summary and a list of
tools), and the tool strip above them is a join. Hovering or focusing a tool
lights every record that used it and dims the rest, which answers the question a
reader actually has: not "what does he know?" but "where did he actually use
it?".

On top of that sits an AI chatbot that answers questions about my work using
only what I have written down, and a full Arabic version of the site, with the
layout mirrored right to left. The source is public at
github.com/mohalansari2005-sys/profile-webpage.

## How the site is built

The front end is Next.js 16 with the App Router, React 19, TypeScript and
Tailwind CSS v4, exported as plain static files (`output: "export"`) and served
by Vercel. Static export is the central constraint: there is no server at
runtime, so no API routes, no middleware and no `redirects` in the Next config,
and anything that needs a backend has to be called from the browser. Most of the
page is server-rendered at build time and ships no JavaScript; only the parts
that hold state (the tool join, the chat, the theme and language toggles, the
scroll-reveal) are client components.

Design tokens live once in CSS custom properties and map to Tailwind utilities.
Three colours carry meaning: green marks structure, amber marks a matched row
and appears nowhere else, and a dim grey is for secondary text. Motion is
kept to a few deliberate moments and is switched off under `prefers-reduced-motion`.

## The content pipeline

Everything on the page and everything the chatbot knows comes from one place:
Markdown files in `content/`. Each record has frontmatter (title, organisation,
period, tools, summary) and a body of longer prose. A single Node loader
validates the whole corpus once and generates two committed artifacts: a
TypeScript module for the site, which contains only the frontmatter fields, and
a JSON file for the chatbot's backend, which also contains each record's prose.
Because one loader feeds both, the page and the bot cannot disagree about what a
record says.

Validation is strict on purpose. A tool id in a record must match a declared
tool, because that string is the join key the tool strip filters on; a typo used
to render nothing silently and is now a build error naming the record and the
unknown tool. Arabic display text lives in separate `*_ar` fields that go to the
site but are stripped from the chatbot's corpus, and a test enforces that.

## The chatbot

The chat backend is a Django and Django REST Framework service. Each question
runs through a five-node LangGraph: condense, relevance, retrieve, generate,
log. Condense rewrites a follow-up into a standalone question, and for Arabic
questions it also produces an English search query, because the corpus is in
English. Relevance is a scope gate that classifies what the question is about.
Retrieve embeds the query with OpenAI's text-embedding-3-small (1536
dimensions), finds the nearest chunks with pgvector cosine distance in
PostgreSQL, and expands each hit to its whole record so the answer can carry the
detail. Generate answers from that context in the language of the question,
naming the chunks it used. Log writes a row for every turn.

A record is split into a summary chunk plus one chunk per section heading. The
ingest command is idempotent: it hashes each chunk's text together with the
embedding model name and only re-embeds what changed, so re-running it costs
nothing when the corpus has not moved, and changing the embedding model
re-embeds everything instead of leaving stale vectors behind.

## Guardrails and cost

Grounding is enforced in Python, not requested in a prompt. The generate step
returns schema-validated JSON with the chunk ids it used; if those are not a
subset of what retrieval returned, or the model says the context was
insufficient, the answer is thrown away and replaced with a refusal before it
leaves the server. The scope gate fails closed: a response it cannot parse is a
refusal.

Two models split the work. A small, fast model (gpt-4.1-nano) runs condense and
relevance, and gpt-4.1-mini writes the answer. OpenAI serves both generation and
embeddings; Groq was tried first for its free tier and rejected because it has
no embeddings endpoint, which would have needed a second provider and key.

The API key never reaches the browser, which is the reason the backend exists at
all. Requests are rate limited per IP (10 a minute by default) with a global
daily cap that acts as the spend limit, both counted in Redis. Chat logs store a
salted SHA-256 of the client address, never the address itself.

## Testing and CI

The backend test suite stubs every OpenAI call, so it needs no key and costs
nothing. A separate opt-in set of evaluation tests calls the real fast model to
check something stubs cannot: whether the prompts judge correctly. They exist
because a scope gate once refused "What is Majara?", treating my own employer as
unrelated to me, while the whole green suite passed, since every other test only
proved the wiring.

The front end has Playwright end-to-end tests that run against the static build
with the chat API mocked, covering the chat, dark mode, the projects carousel,
right-to-left layout and the Arabic pages. The content pipeline has its own Node
tests. A GitHub Actions workflow runs lint, build, the Playwright suite, the
content tests and the backend tests (against real PostgreSQL with pgvector and
Redis service containers) on every pull request, and work is done on a branch
per unit of work with a review before merging.

## Deployment

The front end deploys to Vercel from the main branch. The backend runs with
Docker Compose on a Hetzner VPS, behind Caddy for automatic HTTPS, with
PostgreSQL and Redis in their own containers and Django never exposed directly.
A GitHub Actions workflow deploys it on every push to main that touches the
backend: it pulls, rebuilds the containers, runs the migrations and re-ingests
the content, so the chatbot's knowledge updates when the corpus does.

## Languages, theme and accessibility

The site has a full Arabic version at `/ar`, with English at `/`. Each language
is its own root layout so the `lang` and `dir` attributes are in the first byte
of HTML, the layout mirrors right to left, Arabic uses IBM Plex Sans Arabic
loaded only on that page, and a language toggle remembers the reader's choice.
Dark mode follows the operating system with a toggle to override it, and a small
script sets the theme before first paint so there is no flash. Colours were
checked for contrast, motion respects reduced-motion settings, and the scroll
reveal has a fallback so content is never stuck invisible for readers without
JavaScript.

## Why it is built this way

The AI chat was a deliberate learning exercise: retrieval, agent orchestration
and running my own backend are heavier than a portfolio strictly needs, and I
chose them on purpose to learn them properly. Each feature was written up as a
short spec, and larger ones as a plan, in the repository's `docs/` folder before
any code, and merged only after tests, a review and a manual check in the
browser. The bugs that taught me the most were the ones tests missed: the
over-eager scope gate, Arabic questions being searched directly against an
English corpus (where a transliterated company name means nothing to the
search), and CSS that only worked left to right.
