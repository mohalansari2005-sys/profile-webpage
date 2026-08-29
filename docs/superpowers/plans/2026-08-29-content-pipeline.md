# Content Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `content/` a real markdown corpus and generate `frontend/lib/content.ts` from it, so one set of files is the source of truth for both the rendered site and (later) the chat bot's retrieval.

**Architecture:** A plain Node generator at the repo root reads `content/`, validates it hard, and writes `frontend/lib/content.ts`. The generated file stays committed, so the Vercel build never runs the generator — it just consumes the committed output. Drift is caught by a check script that regenerates into a temp file and diffs.

**Tech Stack:** Node 24 (plain ESM, no TypeScript runner), `gray-matter` + `js-yaml` as dev dependencies, Next.js 16 static export.

**Spec:** `docs/superpowers/specs/2026-08-29-ai-chat-design.md` — Branch 2.

## Global Constraints

- **The rendered site must not change.** Success is measured with `scripts/fingerprint-export.sh` (built in Branch 1). The target is the current value: `bb8c3eed6e2a116e420ba8e12c758e0e62b560d5`.
- **No `.md` file may be created inside `frontend/`.** Tailwind v4's automatic content scan sweeps text files under the project root; prose inside `frontend/` injects dead utility classes into production CSS. This was observed for real in Branch 1.
- **The generator itself must live outside `frontend/`** for the same reason — a `.ts`/`.js` file inside the scan root has its string literals swept for class candidates.
- Exactly two new dev dependencies: `gray-matter`, `js-yaml`. No others.
- `ToolGroup`, `Tool`, `WorkRecord`, `toolById`, `tools`, `experience`, `projects` keep their current exported names and shapes.
- **Order is load-bearing.** `work.tsx` renders `tools` and the record arrays in array order; the corpus must control that order deterministically.
- `main` is not touched. Work lands on `feat/content-pipeline` for review.

---

## Three corrections to the spec, made here

The spec's Branch 2 section was written before Branch 1 surfaced how this repo actually builds. Three of its instructions are wrong as stated:

**1. The generator must NOT be an npm `prebuild` script.** The spec wires it that way. Vercel's Root Directory is `frontend`, and unless "Include files outside the root directory" is enabled, `content/` is absent during a Vercel build — so `prebuild` would fail every deploy. Worth confirming that setting in the dashboard, but the design here does not depend on the answer: because the generated file is committed, Vercel never needs to generate at all. The generator becomes an explicit local script (`npm run content`), plus a `content:check` script that fails if the committed output is stale.

**2. The generator goes in repo-root `scripts/`, not `frontend/scripts/`.** The spec says `frontend/scripts/build-content.ts`. Anything inside `frontend/` is inside Tailwind's content-scan root, so the generator's own string literals — including every tool label and group name — would be scanned as candidate class names. Repo root keeps it out.

**3. It is a `.mjs` file, not `.ts`.** A TypeScript generator needs a TS runner (`tsx` or similar) — a third dependency, for a build script no one type-checks. Plain ESM on Node 24 needs none.

---

## File Structure

**Created (repo root, outside the Tailwind scan root):**
- `scripts/build-content.mjs` — the generator. Reads `content/`, validates, emits `frontend/lib/content.ts`. One responsibility: corpus → typed module.
- `scripts/lib/corpus.mjs` — parsing and validation, importable by the generator and by Branch 3's ingestion so the two never disagree about what the corpus means. Exports `loadCorpus(contentDir)` returning `{ groups, tools, records, byKind }` or throwing an aggregated validation error.

**Created (content corpus):**
- `content/tools.yml` — group order + the tool registry, in render order.
- `content/experience/majara.md`, `content/experience/seet.md`
- `content/projects/corporate-hotel-booking.md`
- `content/about/bio.md`
- `content/faq/availability.md`

**Modified:**
- `frontend/lib/content.ts` — becomes generated output, header-marked, still committed.
- `frontend/package.json` — two dev dependencies, two scripts. No `prebuild`.
- `frontend/components/sections/work.tsx` — one line: import the generated `toolGroups` instead of hardcoding the group order. See Task 5 for why this deliberate deviation from the spec is included.
- `README.md` — document the corpus and the generate/check workflow.

---

### Task 1: Corpus loader and validation

Validation is the whole point of this branch. Today a `tools` key matching no `Tool.id` renders nothing, **silently** — documented as a footgun in `README.md`. This turns it into a build error.

**Files:**
- Create: `scripts/lib/corpus.mjs`
- Create: `scripts/lib/corpus.test.mjs`

**Interfaces:**
- Produces: `loadCorpus(contentDir) -> { groups: string[], tools: Array<{id,label,group}>, records: Array<{id,kind,title,org,period,summary,tools,href?,body}>, byKind: {experience:[], projects:[], about:[], faq:[]} }`. Throws `CorpusError` with an aggregated `.problems` array of human-readable strings. Consumed by Task 2 and by Branch 3's ingestion.

- [ ] **Step 1: Write the failing tests**

Node 24 has a built-in test runner, so this needs no test framework.

```js
// scripts/lib/corpus.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadCorpus, CorpusError } from "./corpus.mjs";

function fixture(files) {
  const dir = mkdtempSync(join(tmpdir(), "corpus-"));
  for (const [rel, body] of Object.entries(files)) {
    const path = join(dir, rel);
    mkdirSync(join(path, ".."), { recursive: true });
    writeFileSync(path, body);
  }
  return dir;
}

const TOOLS = `groups:
  - Build
  - Practice
tools:
  - { id: python, label: Python, group: Build }
  - { id: agile, label: Agile, group: Practice }
`;

const REC = `---
id: exp-a
kind: experience
title: Engineer
org: Acme
period: 2025
tools: [python]
summary: Did things.
---

## Detail
Body prose.
`;

test("loads tools in declared order", () => {
  const c = loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC }));
  assert.deepEqual(c.tools.map((t) => t.id), ["python", "agile"]);
  assert.deepEqual(c.groups, ["Build", "Practice"]);
});

test("keeps frontmatter and body separate", () => {
  const c = loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC }));
  assert.equal(c.records[0].summary, "Did things.");
  assert.match(c.records[0].body, /Body prose/);
  assert.equal(c.byKind.experience.length, 1);
});

test("rejects a tools key matching no tool id", () => {
  const bad = REC.replace("tools: [python]", "tools: [rust]");
  const err = assert.throws(
    () => loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad })),
    CorpusError,
  );
  assert.match(err.problems.join("\n"), /exp-a.*unknown tool.*rust/i);
});

test("rejects a tool in an undeclared group", () => {
  const bad = TOOLS.replace("group: Practice", "group: Nonsense");
  const err = assert.throws(
    () => loadCorpus(fixture({ "tools.yml": bad, "experience/a.md": REC })),
    CorpusError,
  );
  assert.match(err.problems.join("\n"), /agile.*undeclared group.*Nonsense/i);
});

test("rejects duplicate record ids", () => {
  const err = assert.throws(
    () => loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC, "projects/b.md": REC })),
    CorpusError,
  );
  assert.match(err.problems.join("\n"), /duplicate id.*exp-a/i);
});

test("rejects a record missing a required field", () => {
  const bad = REC.replace("org: Acme\n", "");
  const err = assert.throws(
    () => loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad })),
    CorpusError,
  );
  assert.match(err.problems.join("\n"), /exp-a.*missing.*org/i);
});

test("reports every problem at once, not just the first", () => {
  const bad = REC.replace("tools: [python]", "tools: [rust, go]");
  const err = assert.throws(
    () => loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad })),
    CorpusError,
  );
  assert.equal(err.problems.length, 2);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test scripts/lib/`
Expected: FAIL — `Cannot find module './corpus.mjs'`.

- [ ] **Step 3: Implement the loader**

Required frontmatter fields per record: `id`, `kind`, `title`, `org`, `period`, `summary`, `tools`. Optional: `href`. `kind` must be one of `experience`, `projects`, `about`, `faq`. Records are ordered by filename within each kind, so ordering is deterministic and controlled by the corpus author.

```js
// scripts/lib/corpus.mjs
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import matter from "gray-matter";
import yaml from "js-yaml";

export class CorpusError extends Error {
  constructor(problems) {
    super(`corpus validation failed:\n  - ${problems.join("\n  - ")}`);
    this.name = "CorpusError";
    this.problems = problems;
  }
}

const KINDS = ["experience", "projects", "about", "faq"];
const REQUIRED = ["id", "kind", "title", "org", "period", "summary", "tools"];

export function loadCorpus(contentDir) {
  const problems = [];

  const toolsPath = join(contentDir, "tools.yml");
  if (!existsSync(toolsPath)) throw new CorpusError([`missing ${toolsPath}`]);
  const registry = yaml.load(readFileSync(toolsPath, "utf8")) ?? {};
  const groups = registry.groups ?? [];
  const tools = registry.tools ?? [];

  if (groups.length === 0) problems.push("tools.yml declares no groups");
  const seenTool = new Set();
  for (const tool of tools) {
    if (!tool?.id || !tool?.label || !tool?.group) {
      problems.push(`tool entry missing id/label/group: ${JSON.stringify(tool)}`);
      continue;
    }
    if (seenTool.has(tool.id)) problems.push(`duplicate tool id: ${tool.id}`);
    seenTool.add(tool.id);
    if (!groups.includes(tool.group)) {
      problems.push(`tool "${tool.id}" is in undeclared group "${tool.group}"`);
    }
  }

  const records = [];
  const seenRecord = new Set();
  for (const kind of KINDS) {
    const dir = join(contentDir, kind);
    if (!existsSync(dir)) continue;
    for (const file of readdirSync(dir).filter((f) => f.endsWith(".md")).sort()) {
      const where = `${kind}/${file}`;
      const { data, content } = matter(readFileSync(join(dir, file), "utf8"));
      const missing = REQUIRED.filter((f) => data[f] === undefined);
      const id = data.id ?? where;
      if (missing.length) problems.push(`${id} (${where}) missing: ${missing.join(", ")}`);
      if (data.kind !== undefined && data.kind !== kind) {
        problems.push(`${id} (${where}) declares kind "${data.kind}" but sits in ${kind}/`);
      }
      if (data.id !== undefined) {
        if (seenRecord.has(data.id)) problems.push(`duplicate id: ${data.id} (${where})`);
        seenRecord.add(data.id);
      }
      for (const toolId of data.tools ?? []) {
        if (!seenTool.has(toolId)) {
          problems.push(`${id} (${where}) references unknown tool "${toolId}"`);
        }
      }
      records.push({
        id: data.id, kind, title: data.title, org: data.org, period: data.period,
        summary: typeof data.summary === "string" ? data.summary.trim() : data.summary,
        tools: data.tools ?? [], ...(data.href ? { href: data.href } : {}),
        body: content.trim(), source: where,
      });
    }
  }

  if (problems.length) throw new CorpusError(problems);

  const byKind = Object.fromEntries(KINDS.map((k) => [k, records.filter((r) => r.kind === k)]));
  return { groups, tools, records, byKind };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test scripts/lib/`
Expected: 7/7 passing.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/corpus.mjs scripts/lib/corpus.test.mjs
git commit -m "Add corpus loader with hard validation

Turns the silent footgun documented in README — a tools key matching no
Tool.id renders nothing, silently — into an aggregated build error that
reports every problem at once rather than the first."
```

---

### Task 2: The generator

**Files:**
- Create: `scripts/build-content.mjs`
- Test: `scripts/build-content.test.mjs`

**Interfaces:**
- Consumes: `loadCorpus` from Task 1.
- Produces: `node scripts/build-content.mjs [--check]`. Default writes `frontend/lib/content.ts`. `--check` writes nothing, exits 0 if the committed file matches what would be generated, exits 1 with a diff hint otherwise.

- [ ] **Step 1: Write the failing test**

```js
// scripts/build-content.test.mjs
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
```

That last test matters: the body is for retrieval only. If it leaked into `content.ts` it would ship to every visitor **and** land inside Tailwind's scan root.

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test scripts/build-content.test.mjs`
Expected: FAIL — `renderModule` is not exported.

- [ ] **Step 3: Implement the generator**

Use `JSON.stringify` for every emitted string so escaping is the language's problem, not ours. Verified on Node 24: `JSON.stringify('He said "hi" — really')` yields `"He said \\"hi\\" — really"` — escaped double quotes, em dash left as a literal character. That is what the Step 1 test asserts.

```js
// scripts/build-content.mjs
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test scripts/build-content.test.mjs`
Expected: 6/6 passing.

- [ ] **Step 5: Commit**

```bash
git add scripts/build-content.mjs scripts/build-content.test.mjs
git commit -m "Add the content.ts generator

Emits the ToolGroup union and toolGroups array from the corpus's declared
group order, so group order has one source of truth. Record bodies are
deliberately excluded — they are retrieval material, and shipping them
would both bloat the bundle and put prose inside Tailwind's scan root."
```

---

### Task 3: Write the corpus

Transcribe today's `frontend/lib/content.ts` into markdown **exactly** — same strings, same order — then add body prose. The page must not change, so the frontmatter is a faithful port; the bodies are new material the page never shows.

**Files:**
- Create: `content/tools.yml`, `content/experience/majara.md`, `content/experience/seet.md`, `content/projects/corporate-hotel-booking.md`, `content/about/bio.md`, `content/faq/availability.md`

- [ ] **Step 1: Write `content/tools.yml`**

Filenames set order within a kind, so `experience/majara.md` sorts before `experience/seet.md` — matching today's array order. Verify that holds before relying on it.

```yaml
# Group order controls how the tool strip renders. Tool order within the file
# controls order inside each group. Both are load-bearing.
groups:
  - Build
  - Data & infrastructure
  - Practice

tools:
  - { id: python,           label: Python,            group: Build }
  - { id: javascript,       label: JavaScript,        group: Build }
  - { id: fastapi,          label: FastAPI,           group: Build }
  - { id: sqlalchemy,       label: SQLAlchemy,        group: Build }
  - { id: rest-apis,        label: REST APIs,         group: Build }
  - { id: langchain,        label: LangChain,         group: Build }
  - { id: postgres,         label: PostgreSQL,        group: Data & infrastructure }
  - { id: redis,            label: Redis,             group: Data & infrastructure }
  - { id: celery,           label: Celery,            group: Data & infrastructure }
  - { id: docker,           label: Docker,            group: Data & infrastructure }
  - { id: pytest,           label: pytest,            group: Data & infrastructure }
  - { id: systems-analysis, label: Systems analysis,  group: Practice }
  - { id: agile,            label: Agile,             group: Practice }
  - { id: sdlc,             label: SDLC,              group: Practice }
  - { id: b2b,              label: B2B software,      group: Practice }
```

- [ ] **Step 2: Port the three existing records verbatim**

Copy each `summary` **character for character** from the current `frontend/lib/content.ts` — em dashes, parentheses and all. Any drift changes the rendered page and fails the fingerprint check in Task 6.

`content/experience/majara.md` frontmatter — note the title is currently `"Product Engineering intern"` in `lib/content.ts`; use whatever the file says at implementation time, do not "correct" it:

```markdown
---
id: exp-majara
kind: experience
title: Product Engineering intern
org: Majara — Riyadh, hybrid
period: Nov 2025 — Present
tools: [python, javascript, rest-apis, langchain, systems-analysis, agile, sdlc, b2b]
summary: >-
  Built and integrated Python backend services and REST APIs for a B2B product,
  and prototyped new product capabilities from requirements through to working
  software.
---

## What the work actually involved

Prose the page never shows. This is what the chat bot answers from — the
specific services, the integrations, what was hard, what shipped.
```

`>-` folds the block into a single space-joined line with no trailing newline, which is what reproduces the current single-line string. Verify the folded result matches the original exactly.

Do the same for `content/experience/seet.md` (`id: exp-seet`, `tools: []`) and `content/projects/corporate-hotel-booking.md` (`id: proj-booking-backend`, `kind: projects`), copying their summaries verbatim from the current file.

- [ ] **Step 3: Add the two corpus-only records**

These have no page representation — they exist purely for retrieval. They still need every required frontmatter field; use `tools: []` where none apply.

`content/about/bio.md` (`id: about-bio`, `kind: about`) and `content/faq/availability.md` (`id: faq-availability`, `kind: faq`), each with a short factual body. Keep them truthful and first-person-consistent with the rest of the site.

- [ ] **Step 4: Verify the corpus loads clean**

Run: `node -e "import('./scripts/lib/corpus.mjs').then(m=>{const c=m.loadCorpus('content');console.log(c.tools.length,'tools',c.records.length,'records');console.log(c.byKind.experience.map(r=>r.id));})"`
Expected: `15 tools 5 records` and `[ 'exp-majara', 'exp-seet' ]` in that order.

- [ ] **Step 5: Commit**

```bash
git add content/
git commit -m "Add the markdown corpus

Frontmatter is a verbatim port of lib/content.ts so the page is unchanged.
Bodies are new: the depth the page never showed, which is what the chat
feature will retrieve from. about/ and faq/ have no page representation at
all — they exist only for retrieval."
```

---

### Task 4: Generate, wire the scripts, and prove the output is identical

**Files:**
- Modify: `frontend/lib/content.ts` (becomes generated), `frontend/package.json`

- [ ] **Step 1: Add the dependencies and scripts**

```bash
cd frontend
npm install --save-dev gray-matter js-yaml
npm pkg set scripts.content="node ../scripts/build-content.mjs"
npm pkg set scripts.content:check="node ../scripts/build-content.mjs --check"
```

Deliberately **no** `prebuild`. Vercel's Root Directory is `frontend` and by default it does not upload files outside that directory, so `content/` is absent during a Vercel build. The committed `content.ts` is what deploys; `content:check` is what stops it going stale.

- [ ] **Step 2: Snapshot the current file, then generate over it**

```bash
cd /Users/mohammed/Desktop/profile-webpage
cp frontend/lib/content.ts /tmp/content-before.ts
npm --prefix frontend run content
```

- [ ] **Step 3: Compare semantically, not textually**

The generated file will differ in comments and formatting — that is expected and fine. What must be identical is the *data*. Compare the parsed exports rather than the text:

```bash
cd frontend
cat > /tmp/cmp.mjs <<'EOF'
const a = await import("/tmp/content-before.ts");
const b = await import("./lib/content.ts");
const pick = (m) => JSON.stringify({
  tools: m.tools, experience: m.experience, projects: m.projects,
});
console.log(pick(a) === pick(b) ? "IDENTICAL DATA" : "DIFFERS");
if (pick(a) !== pick(b)) { console.log("before:", pick(a)); console.log("after: ", pick(b)); }
EOF
npx tsx /tmp/cmp.mjs 2>/dev/null || echo "no tsx — fall back to the Task 6 fingerprint check, which is authoritative"
```

If `tsx` is unavailable, skip this step rather than adding a dependency for it; Task 6's fingerprint comparison is the authoritative test and catches any data drift through the rendered output.

- [ ] **Step 4: Verify `content:check` actually detects staleness**

A check that cannot fail is worthless.

```bash
cd /Users/mohammed/Desktop/profile-webpage
npm --prefix frontend run content:check          # expect: exit 0, "up to date"
printf '\n// drift\n' >> frontend/lib/content.ts
npm --prefix frontend run content:check; echo "exit=$?"   # expect: exit 1, "is stale"
npm --prefix frontend run content                # regenerate, back to clean
npm --prefix frontend run content:check          # expect: exit 0 again
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/content.ts frontend/package.json frontend/package-lock.json
git commit -m "Generate lib/content.ts from the corpus

Adds gray-matter and js-yaml as dev dependencies and two scripts: content
(regenerate) and content:check (fail if the committed output is stale).

Deliberately not wired as prebuild — Vercel's Root Directory is frontend
and it does not upload content/, so a prebuild generator would fail every
deploy. The committed file is what ships."
```

---

### Task 5: Remove the duplicated group order

**This is a deliberate deviation from the spec**, which says `work.tsx` needs no changes. It needs one. `work.tsx:15` hardcodes `const groupOrder: ToolGroup[] = ["Build", "Data & infrastructure", "Practice"]`, which is a second source of truth for group order in a branch whose entire purpose is to establish a single one. Worse, the failure is asymmetric: *removing* a group from the corpus produces a type error, but *adding* one silently fails to render it. One line fixes it.

**Files:**
- Modify: `frontend/components/sections/work.tsx` (the import block and line 15)

**Interfaces:**
- Consumes: `toolGroups` from the generated `@/lib/content` (Task 2).

- [ ] **Step 1: Import `toolGroups` and delete the literal**

Add `toolGroups` to the existing import from `@/lib/content`, then replace line 15:

```ts
const groupOrder: ToolGroup[] = ["Build", "Data & infrastructure", "Practice"];
```

with:

```ts
const groupOrder = toolGroups;
```

If `ToolGroup` is now unused in that file, remove it from the import — `npm run lint` will say so.

- [ ] **Step 2: Verify the rendered order is unchanged**

Run: `cd frontend && npm run lint && rm -rf out && npm run build`
Then: `cd .. && ./scripts/fingerprint-export.sh frontend/out`
Expected: `bb8c3eed6e2a116e420ba8e12c758e0e62b560d5`. Because `tools.yml` declares the groups in today's order, the rendering is byte-identical.

- [ ] **Step 3: Prove the coupling is now real**

```bash
# temporarily append a fourth group and a tool in it
# then regenerate and confirm the new group renders without touching work.tsx
```

Add a throwaway group to `content/tools.yml` with one tool in it, run `npm --prefix frontend run content`, rebuild, and confirm the new group appears in the tool strip. Then revert `tools.yml`, regenerate, rebuild, and confirm the fingerprint returns to `bb8c3eed...`. Leave no trace of the throwaway group in the commit.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/sections/work.tsx
git commit -m "Take group order from the corpus instead of a literal

work.tsx hardcoded the three group names, a second source of truth for
ordering. Removing a group from the corpus was a type error but adding one
silently failed to render. Now content/tools.yml decides."
```

---

### Task 6: Verification

**Files:** none — verification only.

- [ ] **Step 1: The site is unchanged**

```bash
cd /Users/mohammed/Desktop/profile-webpage
cd frontend && rm -rf out && npm run build && cd ..
./scripts/fingerprint-export.sh frontend/out
```

Expected: exactly `bb8c3eed6e2a116e420ba8e12c758e0e62b560d5`. This is the branch's central claim. If it differs, the corpus transcription drifted from the original strings — diff the rendered `frontend/out/index.html` against a build of `main` to find which record changed.

- [ ] **Step 2: Validation actually fails the way it should**

```bash
sed -i '' 's/tools: \[python,/tools: [rust,/' content/experience/majara.md
npm --prefix frontend run content; echo "exit=$?"
```

Expected: exit 1, naming `exp-majara` and the unknown tool `rust`. Then restore:

```bash
sed -i '' 's/tools: \[rust,/tools: [python,/' content/experience/majara.md
npm --prefix frontend run content && npm --prefix frontend run content:check
```

- [ ] **Step 3: Unit tests and lint**

```bash
node --test scripts/
cd frontend && npm run lint
```

Expected: all tests pass, lint clean.

- [ ] **Step 4: No prose leaked into the scan root**

```bash
grep -rn "This is what the chat bot answers from" frontend/ --include='*.ts' --include='*.tsx' && echo "FAIL: body prose reached frontend/" || echo "ok: bodies stayed in content/"
find frontend -name '*.md' -not -path '*/node_modules/*'
```

Expected: the grep finds nothing, and the only `.md` under `frontend/` is the pre-existing generated `AGENTS.md`.

- [ ] **Step 5: Clean-clone check**

```bash
rm -rf /tmp/cp-check && git clone -q --branch feat/content-pipeline . /tmp/cp-check
cd /tmp/cp-check/frontend && npm ci >/dev/null 2>&1 && npm run build 2>&1 | tail -3
cd /tmp/cp-check && ./scripts/fingerprint-export.sh frontend/out
cd /tmp/cp-check && npm --prefix frontend run content:check
rm -rf /tmp/cp-check
```

Expected: build succeeds, fingerprint matches, and `content:check` passes — proving the committed `content.ts` is genuinely in sync with the committed corpus.

- [ ] **Step 6: Update `README.md`**

Document: the corpus lives in `content/`; `frontend/lib/content.ts` is generated and must not be hand-edited; `npm run content` regenerates and `npm run content:check` guards against staleness; the generator is deliberately not a `prebuild` step and why. Replace the existing "Content lives in `lib/content.ts`" section, keeping its warning about tool keys but noting it is now a hard build error rather than a silent one. Commit.

- [ ] **Step 7: Hand back for review**

Report the fingerprint match, the clean-clone result, and the deliberate `work.tsx` deviation from the spec.

---

## Self-Review

**Spec coverage** — Branch 2 of the spec asks for: the `content/` tree (Task 3), frontmatter carrying page fields and body carrying bot depth (Tasks 1, 3), a generator writing `frontend/lib/content.ts` (Task 2), validation turning the silent tool-key footgun into a build error (Tasks 1, 6), unchanged types and exports (Task 2), `gray-matter` (Task 4), and the "site looks exactly the same" test (Task 6). All covered.

**Deliberate deviations, all flagged in-place:** generator is `.mjs` at repo root rather than `.ts` under `frontend/` (Tailwind scan root + no TS runner); not wired as `prebuild` (Vercel Root Directory does not include `content/`); `js-yaml` added as a second dependency (`tools.yml` is standalone YAML, not frontmatter); `work.tsx` gets a one-line change (Task 5) to remove a duplicated group order.

**Placeholder scan:** none. Task 3 Steps 2–3 intentionally do not inline the full record text, because the authoritative strings must be copied from the live file at implementation time rather than from this document — copying them here would create a third source of truth and risk transcription drift. The step says exactly which file to copy from and what must match.

**Type consistency:** `loadCorpus` returns `{groups, tools, records, byKind}` in Task 1 and is consumed with those exact keys in Task 2's `renderModule`. `renderModule(corpus)` is exported in Task 2 and imported by its own test. `toolGroups` is emitted in Task 2 and consumed in Task 5.
