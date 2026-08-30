import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { loadCorpus, CorpusError } from "./lib/corpus.mjs";

const s = (v) => JSON.stringify(v);

function renderRecord(r) {
  const lines = [
    `  {`,
    `    id: ${s(r.id)},`,
    `    title: ${s(r.title)},`,
    `    org: ${s(r.org)},`,
    `    period: ${s(r.period)},`,
    `    summary: ${s(r.summary)},`,
    `    tools: [${r.tools.map(s).join(", ")}],`,
  ];
  if (r.href) lines.push(`    href: ${s(r.href)},`);
  lines.push(`  },`);
  return lines.join("\n");
}

export function renderModule(corpus) {
  return `/**
 * GENERATED FILE — DO NOT EDIT.
 *
 * Written by scripts/build-content.mjs from the markdown corpus in content/.
 * Edit the corpus, then run \`npm run content\` from the repo root.
 *
 * Only the fields the page renders live here. Each record's body prose stays
 * in content/ and is read by the chat backend's ingestion, never shipped to
 * the browser.
 */

export type ToolGroup = ${corpus.groups.map(s).join(" | ")};

export const toolGroups: ToolGroup[] = [${corpus.groups.map(s).join(", ")}];

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
${corpus.tools.map((t) => `  { id: ${s(t.id)}, label: ${s(t.label)}, group: ${s(t.group)} },`).join("\n")}
];

export const experience: WorkRecord[] = [
${corpus.byKind.experience.map(renderRecord).join("\n")}
];

export const projects: WorkRecord[] = [
${corpus.byKind.projects.map(renderRecord).join("\n")}
];

export const toolById = new Map(tools.map((tool) => [tool.id, tool]));
`;
}

export function renderCorpusJson(corpus) {
  return JSON.stringify({
    generatedBy: "scripts/build-content.mjs — do not edit; run `npm run content`",
    groups: corpus.groups,
    tools: corpus.tools,
    records: corpus.records,
  }, null, 2) + "\n";
}

const here = dirname(fileURLToPath(import.meta.url));
const CONTENT = join(here, "..", "content");
const TARGET = join(here, "..", "frontend", "lib", "content.ts");
const CORPUS_JSON = join(here, "..", "backend", "corpus.json");

if (import.meta.main) {
  try {
    const corpus = loadCorpus(CONTENT);
    const artifacts = [
      { path: TARGET, next: renderModule(corpus), label: "frontend/lib/content.ts" },
      { path: CORPUS_JSON, next: renderCorpusJson(corpus), label: "backend/corpus.json" },
    ];
    if (process.argv.includes("--check")) {
      const stale = artifacts.filter(
        (a) => (existsSync(a.path) ? readFileSync(a.path, "utf8") : "") !== a.next,
      );
      if (stale.length) {
        for (const a of stale) console.error(`${a.label} is stale.`);
        console.error("Run `npm run content` from the repo root and commit the result.");
        process.exit(1);
      }
      console.log("generated artifacts are up to date");
    } else {
      for (const a of artifacts) {
        writeFileSync(a.path, a.next);
        console.log(`wrote ${a.path}`);
      }
    }
  } catch (e) {
    if (e instanceof CorpusError) {
      console.error("corpus validation failed:");
      for (const problem of e.problems) console.error(`  - ${problem}`);
      process.exit(1);
    }
    throw e;
  }
}
