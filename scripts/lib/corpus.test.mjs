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
period: "2025"
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
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /exp-a.*unknown tool.*rust/i);
});

test("rejects a tool in an undeclared group", () => {
  const bad = TOOLS.replace("group: Practice", "group: Nonsense");
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": bad, "experience/a.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /agile.*undeclared group.*Nonsense/i);
});

test("rejects duplicate record ids", () => {
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC, "projects/b.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /duplicate id.*exp-a/i);
});

test("rejects a record missing a required field", () => {
  const bad = REC.replace("org: Acme\n", "");
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /exp-a.*missing.*org/i);
});

test("reports every problem at once, not just the first", () => {
  const bad = REC.replace("tools: [python]", "tools: [rust, go]");
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.equal(err.problems.length, 2);
});

test("rejects an unknown subdirectory in content", () => {
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "blog/a.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /unknown.*kind.*blog/i);
});

test("rejects a non-array tools value with clear error", () => {
  const bad = REC.replace("tools: [python]", "tools: python");
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /tools.*must be a list/i);
});

test("rejects non-string summary, title, org, period", () => {
  const bad = REC.replace("summary: Did things.", "summary: 12345");
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /summary.*must be a string/i);
});

test("rejects a stray record file at the corpus root", () => {
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC, "orphan.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /unexpected file "orphan\.md".*corpus root/i);
});

test("rejects a non-.md file inside a kind directory", () => {
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC, "experience/x.markdown": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /unexpected file "experience\/x\.markdown"/i);
});

test("rejects a subdirectory inside a kind directory", () => {
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": REC, "experience/2024/x.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /unexpected subdirectory "experience\/2024"/i);
});

test("rejects a declared group with zero tools", () => {
  const bad = `groups:
  - Build
  - Practice
  - Empty
tools:
  - { id: python, label: Python, group: Build }
  - { id: agile, label: Agile, group: Practice }
`;
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": bad, "experience/a.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /group "Empty" has no tools/i);
});

test("rejects a duplicate group name", () => {
  const bad = `groups:
  - Build
  - Build
tools:
  - { id: python, label: Python, group: Build }
`;
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": bad, "experience/a.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /duplicate group name: "Build"/i);
});

test("rejects a duplicate tool id inside one record's tools list", () => {
  const bad = REC.replace("tools: [python]", "tools: [python, python]");
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": TOOLS, "experience/a.md": bad }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /exp-a.*repeats tool "python"/i);
});

test("rejects a non-string group name", () => {
  const bad = `groups:
  - Build
  - 2026
tools:
  - { id: python, label: Python, group: Build }
`;
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": bad, "experience/a.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /group name must be a non-empty string, got 2026/i);
});

test("rejects malformed tools.yml with a readable error", () => {
  const badYaml = `groups:
  - Build
tools: [
  { id: python, label: Python, group: Build }
`;
  let err;
  try {
    loadCorpus(fixture({ "tools.yml": badYaml, "experience/a.md": REC }));
    assert.fail("Expected CorpusError to be thrown");
  } catch (e) {
    assert(e instanceof CorpusError);
    err = e;
  }
  assert.match(err.problems.join("\n"), /tools.yml.*parse/i);
});
