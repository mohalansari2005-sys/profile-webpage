/**
 * GENERATED FILE — DO NOT EDIT.
 *
 * Written by scripts/build-content.mjs from the markdown corpus in content/.
 * Edit the corpus, then run `npm run content` from the repo root.
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
  { id: "full-stack", label: "Full-stack", group: "Build" },
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
    title: "Product Engineering Intern",
    org: "Majara — Riyadh, hybrid",
    period: "Nov 2025 — Present",
    summary: "Worked across full-stack development and product development, translating requirements and functional needs into prototypes and product features from concept through to working software.",
    tools: ["python", "javascript", "rest-apis", "full-stack", "systems-analysis", "agile", "sdlc", "b2b"],
  },
  {
    id: "exp-seet",
    title: "Business Development Intern",
    org: "SEET (صيت) — marketing solutions agency, Riyadh",
    period: "Feb — Apr 2025",
    summary: "Worked backward from client objectives to concrete proposals — client meetings, sales pitches, and ongoing relationships. It taught me to translate a loosely defined problem into a solution that's actually useful and deliverable, the same skill that scopes a good engineering requirement.",
    tools: [],
  },
];

export const projects: WorkRecord[] = [
  {
    id: "proj-keyraa",
    title: "Keyraa",
    org: "Majara",
    period: "2026",
    summary: "Keyraa, a corporate hotel booking platform: a FastAPI backend that turns bulk employee trip requests into booked hotels — Amadeus search, bulk booking through Celery workers, and confirmation emails. I built the core flows solo: multi-tenant, idempotent, with retry and backoff around a rate-limited external API. Shelved before launch when industry regulations changed.",
    tools: ["python", "fastapi", "sqlalchemy", "postgres", "redis", "celery", "docker", "rest-apis", "pytest"],
  },
];

export const toolById = new Map(tools.map((tool) => [tool.id, tool]));
