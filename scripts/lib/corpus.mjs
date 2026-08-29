import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import matter from "gray-matter";
import * as yaml from "js-yaml";

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
