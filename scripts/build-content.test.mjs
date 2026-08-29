import { test } from "node:test";
import assert from "node:assert/strict";
import { renderModule } from "./build-content.mjs";

const corpus = {
  groups: ["Build", "Practice"],
  tools: [
    { id: "python", label: "Python", group: "Build" },
    { id: "agile", label: "Agile", group: "Practice" },
  ],
  byKind: {
    experience: [{ id: "exp-a", title: "Engineer", org: "Acme", period: "2025",
                   summary: 'He said "hi" — really', tools: ["python"] }],
    projects: [{ id: "proj-b", title: "Thing", org: "Acme", period: "2026",
                 summary: "Built it.", tools: ["python", "agile"], href: "https://x.test" }],
    about: [], faq: [],
  },
};

test("emits the ToolGroup union from declared groups, in order", () => {
  const out = renderModule(corpus);
  assert.match(out, /export type ToolGroup = "Build" \| "Practice";/);
  assert.match(out, /export const toolGroups: ToolGroup\[\] = \["Build", "Practice"\];/);
});

test("preserves tool order", () => {
  const out = renderModule(corpus);
  assert.ok(out.indexOf('id: "python"') < out.indexOf('id: "agile"'));
});

test("escapes quotes and keeps non-ASCII intact", () => {
  const out = renderModule(corpus);
  // JSON.stringify emits double quotes with escaped inner quotes, and leaves
  // the em dash as a literal character rather than a \u escape.
  assert.ok(out.includes('summary: "He said \\"hi\\" — really"'));
});

test("emits href only when present", () => {
  const out = renderModule(corpus);
  const proj = out.slice(out.indexOf("proj-b"));
  assert.match(proj, /href: "https:\/\/x\.test"/);
  const exp = out.slice(out.indexOf("exp-a"), out.indexOf("proj-b"));
  assert.doesNotMatch(exp, /href:/);
});

test("marks the file as generated", () => {
  assert.match(renderModule(corpus), /generated|do not edit/i);
});

test("does not leak the body prose into the module", () => {
  const withBody = structuredClone(corpus);
  withBody.byKind.experience[0].body = "SECRET_BODY_MARKER";
  assert.doesNotMatch(renderModule(withBody), /SECRET_BODY_MARKER/);
});
