import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { loadCorpus } from "./lib/corpus.mjs";

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
 * Edit the corpus, then run \`npm run content\` from frontend/.
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

const here = dirname(fileURLToPath(import.meta.url));
const CONTENT = join(here, "..", "content");
const TARGET = join(here, "..", "frontend", "lib", "content.ts");

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const next = renderModule(loadCorpus(CONTENT));
  if (process.argv.includes("--check")) {
    const current = existsSync(TARGET) ? readFileSync(TARGET, "utf8") : "";
    if (current !== next) {
      console.error(
        "frontend/lib/content.ts is stale.\n" +
        "Run `npm run content` from frontend/ and commit the result.",
      );
      process.exit(1);
    }
    console.log("content.ts is up to date");
  } else {
    writeFileSync(TARGET, next);
    console.log(`wrote ${TARGET}`);
  }
}
