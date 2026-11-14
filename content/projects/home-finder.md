---
id: "proj-home-finder"
kind: "projects"
title: "Home Finder"
org: "Personal project"
period: "2026"
href: "https://home.alansari.stream"
repo: "https://github.com/mohalansari2005-sys/home-finder"
tools: ["python", "fastapi", "sqlalchemy", "web-scraping", "react", "typescript", "tailwind", "langgraph", "openai-api", "postgres", "postgis", "docker", "pytest", "playwright", "github-actions"]
summary: "A private, Arabic-first web app that helps my family find a home to buy in Riyadh. It scrapes Aqar and Haraj, merges duplicate ads, scores every listing 0–100 against our priorities with a breakdown of why, shows rush-hour drive times, learns from what we save and reject, and plans visit trips. A LangGraph chat assistant changes filters and finds homes from plain Arabic sentences."
title_ar: "بيتنا"
org_ar: "مشروع شخصي"
summary_ar: "تطبيق ويب خاص يعمل بالعربية أولًا، بنيته لمساعدة عائلتي في البحث عن منزل لشرائه في الرياض. يجمع الإعلانات من عقار وحراج، ويدمج الإعلانات المكررة، ويمنح كل عقار درجة من 0 إلى 100 وفق أولوياتنا مع تفصيل أسبابها، ويعرض أوقات القيادة في ساعة الذروة، ويتعلّم مما نحفظه ونرفضه، ويخطط لجولات زيارة العقارات. ويضم مساعد محادثة مبنيًا بـLangGraph يعدّل معايير البحث ويقترح المنازل انطلاقًا من جمل عربية عادية."
---

## What it is

Home Finder (بيتنا in Arabic, "our home") is a private web app I built for my
family's search for a home to buy in Riyadh. It runs at home.alansari.stream
behind a single shared family login, so visitors cannot use it, but the code is
public on GitHub. It is a personal project from November 2026, built through
five milestones: foundation, scoring, the assistant, learning, and visit
planning, all merged.

## The problem it solves

Our search was manual and exhausting. Every day someone scrolled Aqar and
Haraj, saw the same villa posted by three brokers, opened each ad to find its
size and age, pasted the location into a map to guess the morning school run,
and shared screenshots in the family group. We lost track of what we liked,
what we had rejected and why, and which sellers we had called. We did not need
another listings site. We needed something to do the tedious part: read
everything, remember our priorities, and bring back only the homes worth a
look, with reasons.

## What it does

- Scrapes Aqar and Haraj on a schedule and merges duplicates of the same home
  posted by different brokers.
- Extracts sizes, ages and other details buried in ad text, and labels anything
  it cannot find as unknown instead of guessing.
- Shows rush-hour drive times to the four places the family goes: school,
  work, university and King Khalid International Airport.
- Gives every listing an explainable 0 to 100 score ("why 86?") from weights
  the family sets, after hard filters such as budget, districts, property type,
  bedrooms, maximum drive time, building age and street width.
- Flags only new or changed homes, tracks price history and price drops, and
  marks listings that were removed.
- Learns from saves, rejects and visit ratings, and suggests new filters from
  repeated reject reasons, such as "filter out buildings older than 20 years?".
- Plans visit days: groups saved homes by district, orders the stops, sets time
  slots, adds WhatsApp links to contact sellers, and checks before the trip that
  the ads are still live.
- Has a map with price pins coloured by score, a side-by-side compare view for
  two to four homes, and a settings page with a history of every preference
  change.
- Is a right-to-left Arabic PWA that installs to the home screen, with a layout
  designed separately for phone, iPad and desktop.

## Scoring and learning are plain code

Scoring has two steps and no AI. Hard filters decide whether a listing appears
at all, and an unknown value never fails a filter, so a home is not hidden just
because the ad left something out. The score then rates every listing that
passes on 18 factors, each normalised to between 0 and 1: drive times, price
against budget, built and land area, building age, street width, number of
streets, facing direction, deed type, rooms, and features such as a maid's
room, driver's room, yard or elevator. The score is their weighted average
times 100. Factors an ad does not mention are left out and listed as missing,
and every score comes with its breakdown of what pushed it up, what pulled it
down and what is unknown.

Learning adjusts those weights from what the family actually does. Saves count
as liked and rejects as not liked, and visit ratings count three times as much.
After every 10 new reactions, once there are at least 5 of each, a logistic
regression finds which factors separate liked homes from rejected ones. The
weights move only 30% of the way toward its suggestion, each weight changes by
at most 20% per run, and weights the family has locked are never touched. Every
change is logged with an Arabic explanation. Filter suggestions are simple
rules rather than a model, and nothing changes until someone taps apply.

## Where the LLM is used, and the LangGraph agent

The LLM is used only where language is the actual problem, and it never
invents facts. On the worker, a small OpenAI model reads ad text and fills in
only the fields that are still empty, using structured outputs so the reply is
validated JSON, with every value range-checked before it is saved. Regular
expressions run first where they can.

The chat assistant is a LangGraph agent built with LangChain's create_agent. It
loops: the model reads the conversation, decides whether to call a tool, sees
the result, and repeats until it can answer. Its tools read and update
preferences, search listings, fetch and compare listings, queue a fresh scrape,
show or apply filter suggestions, and suggest or create visit trips. The family
can say "we want a villa in Al Narjis or Al Yasmin for around two million, and
the school matters more than work", and the agent updates the filters and
weights and replies with matching listing cards. The system prompt is in Arabic
and forbids making up listings, prices or distances. Conversations are saved
with LangGraph's Postgres checkpointer so a thread continues on another device,
and replies stream to the browser over server-sent events.

I chose this split on purpose. Scoring, filters and learning are deterministic,
testable and free, so the app keeps working with no API key at all.

## Architecture

The work is split between a small always-on server and my MacBook. A Hetzner
VPS with 1 vCPU and 2 GB of RAM runs nginx, the static web app, a FastAPI
backend (login, feed, chat) and Postgres 16 with PostGIS. It also holds the job
queue, a Postgres table whose jobs are claimed with SELECT ... FOR UPDATE SKIP
LOCKED. The Mac runs a worker that pulls jobs over Tailscale and does the heavy
work: scraping, LLM extraction, geocoding and drive times, photos and learning.
No headless browser runs on the server. The Mac's residential IP is also far
less likely to be blocked than a datacenter IP. When the Mac sleeps, the app
keeps working on stored data and new listings arrive when it wakes. If the Mac
is offline, the assistant can still run one small Aqar search from the server.

Scraping is paced, read-only and done without logging in. Aqar is read through
the same GraphQL endpoint its own web app uses. It sits behind Cloudflare, so
requests go through curl_cffi with browser impersonation, with Playwright as a
fallback. A source is paused, not forced, when it starts blocking, and a health
check pauses an adapter whose results suddenly lose their prices or locations.
Duplicates are merged when two ads are close together, match on area and
price, and have photos with a near-identical perceptual hash.

Spending is capped. Every OpenAI call is metered against a monthly budget, and
when it runs out the assistant says so and the rest of the app carries on.
Geocoding and traffic-aware drive times use TomTom's free tier, so requests are
counted per day and per month against caps set just under the free allowance,
and background work stops at 80% to keep the rest for planning visits. The map
uses MapLibre GL with OpenFreeMap tiles and needs no key.

## Stack and testing

Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Postgres 16 with PostGIS.
Scraping: curl_cffi with a Playwright fallback. Agent: LangGraph with OpenAI,
streamed over SSE. Maps: TomTom Routing and Geocoding, MapLibre GL. Web: React
19, Vite, TypeScript, Tailwind CSS v4, shadcn/ui in right-to-left, TanStack
Query. Deployment: Docker Compose on the server and a launchd service on the
Mac.

Tests use pytest, Vitest and Playwright. Scrapers are tested against saved,
scrubbed responses rather than live sites, and the agent has scripted Arabic
conversations that check which tools it calls. Every change lands through a
pull request that must pass the GitHub Actions jobs for the backend, the web
app, the API image and a secrets scan. The repository is public, so no keys,
place coordinates or seller contacts are committed.
