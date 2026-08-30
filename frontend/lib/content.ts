/**
 * GENERATED FILE — DO NOT EDIT.
 *
 * Written by scripts/build-content.mjs from the markdown corpus in content/.
 * Edit the corpus, then run `npm run content` from frontend/.
 *
 * Only the fields the page renders live here. Each record's body prose stays
 * in content/ and is read by the chat backend's ingestion, never shipped to
 * the browser.
 */

export type ToolGroup = "Build" | "Data & infrastructure" | "Practice";

export const toolGroups: ToolGroup[] = ["Build", "Data & infrastructure", "Practice"];

export type Tool = {
  id: string;
  label: string;
  group: ToolGroup;
};

export type WorkRecord = {
  id: string;
  title: string;
  org: string;
  period: string;
  summary: string;
  tools: string[];
  href?: string;
};

export const tools: Tool[] = [
  { id: "python", label: "Python", group: "Build" },
  { id: "javascript", label: "JavaScript", group: "Build" },
  { id: "fastapi", label: "FastAPI", group: "Build" },
  { id: "sqlalchemy", label: "SQLAlchemy", group: "Build" },
  { id: "rest-apis", label: "REST APIs", group: "Build" },
  { id: "langchain", label: "LangChain", group: "Build" },
  { id: "postgres", label: "PostgreSQL", group: "Data & infrastructure" },
  { id: "redis", label: "Redis", group: "Data & infrastructure" },
  { id: "celery", label: "Celery", group: "Data & infrastructure" },
  { id: "docker", label: "Docker", group: "Data & infrastructure" },
  { id: "pytest", label: "pytest", group: "Data & infrastructure" },
  { id: "systems-analysis", label: "Systems analysis", group: "Practice" },
  { id: "agile", label: "Agile", group: "Practice" },
  { id: "sdlc", label: "SDLC", group: "Practice" },
  { id: "b2b", label: "B2B software", group: "Practice" },
];

export const experience: WorkRecord[] = [
  {
    id: "exp-majara",
    title: "Product Engineering intern",
    org: "Majara — Riyadh, hybrid",
    period: "Nov 2025 — Present",
    summary: "Built and integrated Python backend services and REST APIs for a B2B product, and prototyped new product capabilities from requirements through to working software.",
    tools: ["python", "javascript", "rest-apis", "langchain", "systems-analysis", "agile", "sdlc", "b2b"],
  },
  {
    id: "exp-seet",
    title: "Business Development Intern",
    org: "SEET (صيت) — marketing solutions agency, Riyadh",
    period: "Feb — Apr 2025",
    summary: "Ran client meetings, prepared sales pitches, presented proposals, and managed ongoing client relationships. It taught me to read what a client actually needs and present a practical solution — the other half of the problem-solving process from the engineering side.",
    tools: [],
  },
];

export const projects: WorkRecord[] = [
  {
    id: "proj-booking-backend",
    title: "Corporate hotel booking backend",
    org: "Majara",
    period: "2026",
    summary: "A FastAPI service that turns bulk employee trip requests into booked hotels — Amadeus search, bulk booking through Celery workers, and confirmation emails. I built the core flows solo: multi-tenant, idempotent, with retry and backoff around a rate-limited external API. Shelved before launch when industry regulations changed.",
    tools: ["python", "fastapi", "sqlalchemy", "postgres", "redis", "celery", "docker", "rest-apis", "pytest"],
  },
];

export const toolById = new Map(tools.map((tool) => [tool.id, tool]));
