import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
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

test("the entrypoint guard runs identically through a symlink", () => {
  // process.argv[1] === fileURLToPath(import.meta.url) is false when the
  // script is reached via a symlinked path, because Node realpaths
  // import.meta.url but not argv[1] — the guard silently no-ops instead of
  // running the --check. import.meta.main is realpath-independent, so a
  // direct run and a symlinked run must produce identical output.
  const real = fileURLToPath(new URL("./build-content.mjs", import.meta.url));
  const dir = mkdtempSync(join(tmpdir(), "build-content-symlink-"));
  const link = join(dir, "build-content.mjs");
  symlinkSync(real, link);
  try {
    const direct = execFileSync("node", [real, "--check"], { encoding: "utf8" });
    const viaSymlink = execFileSync("node", [link, "--check"], { encoding: "utf8" });
    assert.equal(viaSymlink, direct);
    assert.match(viaSymlink, /content\.ts is up to date/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
