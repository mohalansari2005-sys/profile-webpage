# Monorepo Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the existing Next.js app from the repo root into `frontend/`, and add empty `backend/` and `content/` siblings, without changing a single byte of the rendered site.

**Architecture:** Pure plumbing on branch `chore/monorepo-layout`. No feature code, no dependency changes, no config rewrites. `tsconfig.json`'s `@/*` alias, `components.json`, `eslint.config.mjs`, and `postcss.config.mjs` are all resolved relative to their own location, so they move unedited. The one file that genuinely must change first is `.gitignore`.

**Tech Stack:** Next.js 16 (static export), TypeScript, Tailwind v4, git, bash.

**Spec:** `docs/superpowers/specs/2026-08-29-ai-chat-design.md` — Branch 1.

## Global Constraints

- **No behaviour change.** The rendered export must be byte-identical modulo Next.js's random build ID. Enforced by `scripts/fingerprint-export.sh`.
- **`.gitignore` is fixed BEFORE anything moves.** Non-negotiable ordering — see the warning in Task 2.
- **No dependency added, removed, or upgraded.** `package.json` and `package-lock.json` move unedited.
- **No source file edited.** Only `.gitignore`, `README.md`, `CLAUDE.md`, and new skeleton files change content. Everything else is a pure rename.
- **`main` is not touched.** All work lands on `chore/monorepo-layout` for review.
- Baseline fingerprint measured on this machine before the move: `714d3ab2db800ce8c5cf51f79222d6e44a5dc05c`. Re-measure your own in Task 1 rather than trusting this value — it is a reference, not an assertion.

---

## File Structure

**Created:**
- `scripts/fingerprint-export.sh` — build-ID-insensitive fingerprint of a static export. The success test for the whole branch. Lives at repo root; it is a repo-level tool, not part of the frontend app.
- `backend/README.md`, `content/README.md` — skeleton placeholders that give the new directories a reason to exist in git (git does not track empty directories).

**Modified:**
- `.gitignore` — de-anchor five rules, add one negation.
- `README.md` — path references, plus a new repo-layout section.
- `CLAUDE.md` — stack reference already says `/frontend` + `/backend`; confirm it now matches reality.

**Renamed (content untouched):**
- `app/`, `components/`, `lib/`, `public/` → `frontend/`
- `package.json`, `package-lock.json`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs`, `eslint.config.mjs`, `components.json`, `AGENTS.md` → `frontend/`

**Deliberately NOT moved:** `.gitignore`, `README.md`, `CLAUDE.md`, `docs/`, `scripts/` stay at the repo root.

**Not tracked by git, handled manually in Task 3:** `node_modules/` (moved), `.next/`, `out/`, `next-env.d.ts`, `tsconfig.tsbuildinfo` (deleted; all regenerate).

---

### Task 1: Fingerprint tool and baseline

The branch's success test has to exist before the change it tests. Two builds of identical source are **not** byte-identical — Next.js embeds a random build ID in 15 files — so a naive `diff -r` would fail every time for reasons unrelated to the move.

**Files:**
- Create: `scripts/fingerprint-export.sh`

**Interfaces:**
- Produces: `scripts/fingerprint-export.sh <out-dir>` → prints a 40-char SHA-1 to stdout. Task 6 consumes it.

- [ ] **Step 1: Create the fingerprint script**

```bash
mkdir -p scripts
cat > scripts/fingerprint-export.sh <<'EOF'
#!/usr/bin/env bash
# Fingerprint a Next.js static export, ignoring the per-build random buildId.
# Two builds of identical source MUST produce the same fingerprint.
# Usage: scripts/fingerprint-export.sh <out-dir>
set -euo pipefail
export LC_ALL=C
d="${1%/}"
id=$(ls "$d/_next/static" | grep -Ev '^(chunks|media)$' | head -1)
find "$d" -type f | while read -r f; do
  rel="${f#"$d"/}"
  if grep -Iq . "$f" 2>/dev/null; then
    h=$(sed "s|$id|__BUILDID__|g" "$f" | shasum | awk '{print $1}')   # text
  else
    h=$(shasum "$f" | awk '{print $1}')                                # binary
  fi
  echo "$h ${rel//$id/__BUILDID__}"
done | sort | shasum | awk '{print $1}'
EOF
chmod +x scripts/fingerprint-export.sh
```

Three details are load-bearing and must not be "simplified": `LC_ALL=C` plus the `grep -Iq .` text/binary split (BSD `sed` throws `RE error: illegal byte sequence` on the `.woff2` fonts otherwise), and `sort` running **after** the build ID is substituted out of the path (sorting raw paths orders the two builds' manifest files differently and produces a spurious mismatch).

- [ ] **Step 2: Prove the test does not produce false failures**

```bash
npm run build >/dev/null 2>&1 && A=$(./scripts/fingerprint-export.sh out)
npm run build >/dev/null 2>&1 && B=$(./scripts/fingerprint-export.sh out)
echo "A=$A"; echo "B=$B"; [ "$A" = "$B" ] && echo PASS || echo FAIL
```

Expected: `PASS`. Two consecutive builds of unmodified source agree.

- [ ] **Step 3: Prove the test does not produce false passes**

```bash
rm -rf /tmp/outC && cp -R out /tmp/outC
sed -i '' 's|Mohammed|Mohammad|' /tmp/outC/index.html
[ "$(./scripts/fingerprint-export.sh out)" != "$(./scripts/fingerprint-export.sh /tmp/outC)" ] && echo PASS || echo FAIL
rm -rf /tmp/outC
```

Expected: `PASS`. A one-word change in rendered output is detected.

- [ ] **Step 4: Record the baseline**

```bash
npm run build >/dev/null 2>&1
./scripts/fingerprint-export.sh out | tee /tmp/baseline-fingerprint.txt
```

Write the printed value down. Task 6 compares against it.

- [ ] **Step 5: Commit**

```bash
git add scripts/fingerprint-export.sh
git commit -m "Add build-ID-insensitive fingerprint for the static export

Next.js embeds a random build ID in 15 of the exported files, so two
builds of identical source are never byte-identical. This normalises the
ID out so 'did the rendered site change?' becomes a single comparable
hash — the success test for the monorepo layout move."
```

---

### Task 2: Fix `.gitignore` before anything moves

**This task MUST complete before Task 3.** Five rules are anchored to the repo root with a leading `/`. The moment `node_modules/` sits at `frontend/node_modules/`, those anchors stop matching and git offers to commit tens of thousands of dependency files. Verified against this repo: `frontend/node_modules`, `frontend/.next`, `frontend/out`, `frontend/coverage`, and `frontend/build` are all currently **NOT IGNORED**.

**Files:**
- Modify: `.gitignore:4`, `:5`, `:14`, `:17`, `:18`, `:21`, `:34`

- [ ] **Step 1: Verify the problem is real before fixing it**

```bash
for p in frontend/node_modules/x frontend/.next/x frontend/out/x frontend/coverage/x frontend/build/x; do
  git check-ignore -q "$p" && echo "IGNORED $p" || echo "NOT IGNORED $p"
done
```

Expected: all five report `NOT IGNORED`. That is the bug this task fixes.

- [ ] **Step 2: De-anchor the five rules and add the `.env.example` negation**

```bash
sed -i '' \
  -e 's|^/node_modules$|node_modules/|' \
  -e 's|^/\.pnp$|.pnp|' \
  -e 's|^/coverage$|coverage/|' \
  -e 's|^/\.next/$|.next/|' \
  -e 's|^/out/$|out/|' \
  -e 's|^/build$|build/|' \
  -e 's|^\.env\*$|.env*\
!.env.example|' \
  .gitignore
git diff .gitignore
```

The `.env*` rule is unanchored already, so it correctly protects `backend/.env` at any depth — but it also swallows `backend/.env.example`, which Branch 3 needs to commit as the variable-name template. The negation fixes that.

- [ ] **Step 3: Verify all seven behaviours**

```bash
for p in frontend/node_modules/x frontend/.next/x frontend/out/x frontend/coverage/x frontend/build/x backend/.env; do
  git check-ignore -q "$p" && echo "ok ignored:     $p" || echo "FAIL not ignored: $p"
done
git check-ignore -q backend/.env.example && echo "FAIL .env.example is ignored" || echo "ok committable: backend/.env.example"
```

Expected: six `ok ignored`, one `ok committable`, zero `FAIL`.

> Verify with `check-ignore -q` and read the **exit code**. Do **not** use `-v` — it exits 0 whenever any rule matches, the `!.env.example` negation included, so it reports success for both files and looks like the negation failed.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "De-anchor gitignore rules and un-ignore .env.example

Five rules were anchored to the repo root with a leading slash, so they
would have stopped matching the moment the app moved into frontend/ —
git would have offered to commit node_modules. Also adds !.env.example,
since the unanchored .env* rule correctly hides backend/.env but was
hiding the committable template alongside it."
```

---

### Task 3: Move the app into `frontend/`

**Files:**
- Rename: 12 tracked paths → `frontend/`
- Move/delete: 5 untracked artifacts

**Interfaces:**
- Produces: `frontend/package.json` — every later command runs from `frontend/`.

- [ ] **Step 1: Move the tracked files with `git mv`**

`git mv` preserves rename detection, so the diff reads as renames rather than mass delete-plus-add.

```bash
mkdir -p frontend
git mv app components lib public \
       package.json package-lock.json next.config.ts tsconfig.json \
       postcss.config.mjs eslint.config.mjs components.json AGENTS.md \
       frontend/
git status --porcelain | head -20
```

`.gitignore`, `README.md`, `CLAUDE.md`, `docs/`, and `scripts/` stay at the root — do not move them.

- [ ] **Step 2: Move `node_modules`, delete the regenerable artifacts**

These are untracked, so `git mv` does not touch them.

```bash
mv node_modules frontend/node_modules
rm -rf .next out tsconfig.tsbuildinfo next-env.d.ts
ls -a | grep -E 'node_modules|\.next|^out$' || echo "root is clean"
```

`next-env.d.ts` and `tsconfig.tsbuildinfo` are gitignored and regenerate on the next build; `.next/` and `out/` are build outputs. npm's `.bin` symlinks are relative, so moving `node_modules` is safe — Step 3 proves it.

- [ ] **Step 3: Confirm git did not pick up dependency files**

```bash
git status --porcelain | wc -l
git status --porcelain | grep -c 'node_modules' || echo "0 node_modules entries — correct"
```

Expected: a small number of rename entries, and **zero** `node_modules` entries. A large number here means Task 2 was skipped — stop and fix `.gitignore` before continuing.

- [ ] **Step 4: Build from the new location and compare the fingerprint**

```bash
cd frontend && npm run build 2>&1 | tail -5 && cd ..
./scripts/fingerprint-export.sh frontend/out
cat /tmp/baseline-fingerprint.txt
```

Expected: the two hashes are identical. If they differ, the move changed the rendered site — do not commit; diff `frontend/out` against the pre-move `out/` to find out why.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Move the Next.js app into frontend/

Pure rename, no file contents changed. tsconfig's @/* alias,
components.json, eslint.config.mjs and postcss.config.mjs all resolve
relative to their own location, so they move unedited.

Verified: the static export fingerprints identically before and after."
```

---

### Task 4: Add the `backend/` and `content/` skeletons

Git does not track empty directories, so each needs one real file.

**Files:**
- Create: `backend/README.md`, `content/README.md`

- [ ] **Step 1: Create both placeholders**

```bash
mkdir -p backend content
cat > backend/README.md <<'EOF'
# backend

Django + DRF service for the AI chat feature. Not yet implemented — see
`docs/superpowers/specs/2026-08-29-ai-chat-design.md`, Branch 3.

Runs via `docker-compose.yml` at the repo root alongside Postgres (pgvector)
and Redis. Secrets live in `backend/.env`, which is gitignored;
`backend/.env.example` documents the variable names.
EOF
cat > content/README.md <<'EOF'
# content

Markdown corpus — the single source of truth for both the rendered site and
the chat bot's retrieval. Not yet populated; see
`docs/superpowers/specs/2026-08-29-ai-chat-design.md`, Branch 2.

Frontmatter carries the structured fields the page renders. The body carries
the long-form prose only the bot retrieves. `frontend/lib/content.ts` becomes
generated from this directory at build time.
EOF
```

- [ ] **Step 2: Verify both are staged**

```bash
git add -A && git status --porcelain
```

Expected: exactly two additions, `backend/README.md` and `content/README.md`.

- [ ] **Step 3: Commit**

```bash
git commit -m "Add backend/ and content/ skeletons

Placeholders so the directories exist in git ahead of Branches 2 and 3.
Each names the spec section that fills it."
```

---

### Task 5: Update `README.md` and `CLAUDE.md`

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: Add a repo-layout section to `README.md`**

Insert immediately after the intro paragraph, before `## Stack`:

````markdown
## Repo layout

```
frontend/   Next.js app, static-exported, deployed on Vercel
backend/    Django + DRF service for the chat feature (not yet built)
content/    Markdown corpus feeding both the site and the bot (not yet built)
docs/       Specs and implementation plans
scripts/    Repo-level tooling
```

Vercel's Root Directory is set to `frontend`. All `npm` commands below run
from inside `frontend/`.
````

- [ ] **Step 2: Update the command block**

`README.md:27-29` currently implies the repo root. Change the fenced block to:

```bash
cd frontend
npm run dev     # dev server on http://localhost:3000
npm run build   # production build; writes the static site to frontend/out/
npm run lint    # ESLint (next/core-web-vitals + TypeScript)
```

- [ ] **Step 3: Re-point the remaining file references**

These lines name files that now live under `frontend/`. Prefix each:

```bash
grep -nE '`(lib/content\.ts|app/globals\.css|components/reveal\.tsx|components/sections/work\.tsx|next\.config\.ts)`' README.md
```

Update each hit to the `frontend/`-prefixed path (e.g. `` `lib/content.ts` `` → `` `frontend/lib/content.ts` ``). Also update the `AGENTS.md` note near the end — it now regenerates at `frontend/AGENTS.md`.

- [ ] **Step 4: Confirm `CLAUDE.md` matches reality**

```bash
grep -nE '/frontend|/backend|gemini' CLAUDE.md
```

The stack reference should already describe `/frontend` + `/backend` and name Gemini for both generation and embeddings. It described the intended layout before this branch existed; it is now accurate. Change nothing unless a line contradicts the delivered structure.

- [ ] **Step 5: Verify no stale root-relative paths remain**

```bash
grep -nE '^\s*-?\s*`?(app|components|lib|public)/' README.md
```

Expected: no hits that refer to source files without a `frontend/` prefix.

- [ ] **Step 6: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "Update docs for the frontend/ layout

Adds a repo-layout section, moves the npm commands into frontend/, and
re-points file references. CLAUDE.md already described this layout."
```

---

### Task 6: Final verification and Vercel handoff

**Files:** none — verification only.

- [ ] **Step 1: Clean-clone build, to prove nothing needed was left untracked**

```bash
rm -rf /tmp/layout-check && git clone -q --branch chore/monorepo-layout . /tmp/layout-check
cd /tmp/layout-check/frontend && npm ci >/dev/null 2>&1 && npm run build 2>&1 | tail -5
cd /tmp/layout-check && ./scripts/fingerprint-export.sh frontend/out
```

Expected: the build succeeds from a clean clone and the fingerprint matches `/tmp/baseline-fingerprint.txt`. This is the strongest check in the plan — it catches anything that only worked because of leftover local state.

- [ ] **Step 2: Lint**

```bash
cd /tmp/layout-check/frontend && npm run lint
```

Expected: clean, matching the pre-move result.

- [ ] **Step 3: Confirm the repo shape**

```bash
cd /Users/mohammed/Desktop/profile-webpage
git ls-files | awk -F/ '{print $1}' | sort -u
```

Expected exactly: `.gitignore`, `CLAUDE.md`, `README.md`, `backend`, `content`, `docs`, `frontend`, `scripts`.

- [ ] **Step 4: Clean up**

```bash
rm -rf /tmp/layout-check
```

- [ ] **Step 5: MANUAL — change Vercel's Root Directory**

This cannot be done from code and is the one step that can break the live site.

1. Vercel dashboard → the `profile-webpage` project → Settings → Build & Deployment.
2. Set **Root Directory** to `frontend`.
3. Save.

Push the branch and confirm the **preview** deploy renders the current site correctly **before** merging to `main`. If Root Directory is still the repo root when the branch merges, production builds will fail — there is no `package.json` at the root any more.

- [ ] **Step 6: Hand back for review**

Per `CLAUDE.md`, `main` is not touched until the diff is reviewed and explicitly confirmed. Report: the fingerprint match, the clean-clone build result, and confirmation that the Vercel preview renders correctly.

---

## Self-Review

**Spec coverage** — Branch 1 of the spec lists: move the 12 tracked paths (Task 3), de-anchor `.gitignore` + `!.env.example` (Task 2), `README.md`/`CLAUDE.md` path updates (Task 5), Vercel Root Directory (Task 6 Step 5), `AGENTS.md` regenerating under `frontend/` (Task 3 Step 1, noted in Task 5 Step 3), and the "build unchanged" verification (Tasks 1 and 6). All covered.

**Two corrections the spec needed, found while planning:**

1. The spec listed `next-env.d.ts` among the files to move. It is gitignored and untracked — `git mv` would fail on it. It is deleted and regenerated instead (Task 3 Step 2).
2. The spec said `.gitignore` paths "must be de-anchored" without flagging that this is an **ordering constraint**. Doing it after the move means git offers to commit `node_modules`. Task 2 now runs before Task 3 and states why.

**Placeholder scan:** none. Every step carries the literal command or file content.

**Type consistency:** the only cross-task interface is `scripts/fingerprint-export.sh <out-dir> → SHA-1 on stdout`, produced in Task 1 and consumed in Tasks 3 and 6 with matching argument shape.
