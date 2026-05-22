---
layout: default
title: PDF → Agents Quickstart
nav_order: 2
---

# PDF → Agents Quickstart
{: .no_toc }

A cell-by-cell walkthrough: scaffold a fresh research-flow project, drop in a PDF, let Claude turn it into memory + GitHub issues + a project board, brainstorm strategies, then spawn a team of agents on the work.

Every cell has an **input** (what you type) and an **output** (what you should see). If your output doesn't match the shape shown, fix that cell before moving on — don't push forward.

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## Prerequisites

You need three tools installed and authenticated **before** running any cell below. `create-research-flow` won't help if these aren't ready.

### Node + npx

`npx` ships with Node ≥ 18.

**Input**

```bash
node --version && npx --version
```

**Output (expected shape)**

```
v20.11.0
10.2.4
```

If `node` is missing: install from [nodejs.org](https://nodejs.org/) or `brew install node` (macOS) / `nvm install --lts`.

### GitHub CLI

`create-research-flow` creates a repo, issues, and a project board — all via `gh`.

**Input**

```bash
gh --version && gh auth status
```

**Output (expected shape)**

```
gh version 2.62.0 (2024-12-04)
github.com
  ✓ Logged in to github.com account <your-user> (keyring)
  - Active account: true
  - Token scopes: 'gist', 'project', 'read:org', 'repo', 'workflow'
```

If not logged in: `gh auth login` (pick HTTPS, paste a token with `repo` + `project` + `workflow` scopes).

> **Two GitHub accounts?** Use separate config dirs and set `GH_CONFIG_DIR=~/.config/gh-<profile>` before each `gh` call. `create-research-flow` honors `GH_CONFIG_DIR` if set.

### Claude Code

**Input**

```bash
claude --version
```

**Output (expected shape)**

```
Claude Code v1.x.x
```

If missing: `npm install -g @anthropic-ai/claude-code`, then `claude` once interactively to log in.

---

## Step 1 — Scaffold the project

Run `create-research-flow` — the published scaffolder that lays down `.claude/`, `memory/`, `sources/`, `experiments/`, `outputs/`, and `CLAUDE.md`, then wires up the GitHub repo, issue templates, and project board.

**Input**

```bash
npx create-research-flow@latest my-research
```

**Output (expected shape)**

```
✔ Project name … my-research
✔ Initialize git repo? … yes
✔ Create GitHub repo? … yes
✔ Create project board? … yes
✔ Install Claude skills? … yes

  Scaffolding into ./my-research …
  ├─ .claude/        skills, hooks, commands
  ├─ memory/         index, log, entity-registry
  ├─ sources/        (empty — drop your inputs here)
  ├─ experiments/    blank scaffold
  ├─ outputs/        evidence, verification, examples, critiques
  └─ CLAUDE.md       conventions

✔ git init + initial commit
✔ Created https://github.com/<you>/my-research
✔ Created project board "my-research" (#1)
✔ Installed 14 Claude skills

  Next:  cd my-research && claude
```

**Input**

```bash
cd my-research && ls
```

**Output**

```
CLAUDE.md   experiments/   memory/   outputs/   pyproject.toml   sources/
.claude/    .github/       .gitignore
```

---

## Step 2 — Start Claude

**Input**

```bash
claude
```

**Output**

```
╭─────────────────────────────────────────╮
│  Claude Code                            │
│  cwd: ~/my-research                     │
│  Project loaded: my-research            │
│  14 skills available · /help for list   │
╰─────────────────────────────────────────╯

>
```

You're now inside Claude with the project context loaded. Every cell from here on is **typed inside Claude**, not your shell.

---

## Step 3 — Drop the PDF in + update memory

Drop your PDF anywhere on disk and just ask Claude in natural language. Claude picks the right skill (`/read-pdf` renders each page as a PNG so figures, tables, and equations survive — text extraction alone would lose them), reads it, and writes the extracted entities, findings, and open questions into `memory/` in the same turn.

**Input (in Claude)**

```
Read this PDF: ~/Downloads/my-paper.pdf

Then update memory:
- Extract entities, findings, and open questions into memory/
- Update memory/index.md
- Append a line to memory/log.md
```

**Output (expected shape)**

```
Copying ~/Downloads/my-paper.pdf → sources/my-paper.pdf
Rendering 18 pages → sources/_pdf-images/my-paper/

Extracted from the PDF:
  • 6 entities       → memory/entities/{slugs}.md
  • 4 findings       → memory/findings/{slugs}.md
  • 3 open questions → memory/open-questions/{slugs}.md

Updated memory/index.md (+13 entries)
Appended to memory/log.md:
  ## [2026-05-22] ingest | my-paper.pdf → 6 entities, 4 findings
```

> The `block-source-modification` hook will reject any later `Edit` against `sources/` — that's intentional. PDFs are immutable once ingested; new insights go in `memory/findings/`.

---

## Step 4 — Open the parent issue + add to the project board

Memory is populated. Now turn the research goal into a tracked GitHub issue and put it on the board, so the hypothesis agents you spawn later have something to link their sub-issues against.

**Input (in Claude)**

```
Based on what you just ingested, open a parent research-goal issue:
- Use .github/ISSUE_TEMPLATE/research-goal.md
- Title: research(my-paper): <one-line goal from the abstract>
- Label: research-goal
- Body should link to the memory pages you created

Then add the issue to the project board in the Backlog column. Print
the issue URL when done.
```

**Output (expected shape)**

```
Opened parent issue:
  https://github.com/<you>/my-research/issues/1
  Title: research(my-paper): <goal extracted from abstract>
  Labels: research-goal

Added to project board "my-research" → Backlog
```

---

## Step 5 — Brainstorm strategies

Ask Claude to propose 3–5 distinct hypothesis angles for issue #1, each with confirm/kill criteria and a rough work estimate; you greenlight which to spawn as sub-issues.

---

## Step 6 — Spawn the agent team

For each greenlit hypothesis sub-issue, dispatch a worktree-isolated Agent on its own `hypothesis/GH-<id>-<slug>` branch; they run in parallel and comment back on their sub-issues when done.

---

## What you have now

After Step 6 the project state is:

- **`memory/`** populated with entities, findings, open questions from the PDF
- **GitHub issue #1** = parent research goal, on the board's Backlog column
- **N sub-issues** = greenlit hypotheses, each on its own branch with an agent working
- **No commits to `main`** — the `block-commit-protected-branch` hook enforces this; everything lives on `research/`, `hypothesis/`, or `synthesis/` branches

The loop from here is the standard research-flow loop:

1. Agents finish → `/synthesize` their findings into themes
2. `/experiment` for anything needing compute (see `/vastai` skill for GPU rental)
3. `/evidence` + `/verify` + `/examples` + `/critique` for the validation layer
4. `/distill` to extract decisions, `/lint` to keep memory clean

See [Sample Pipeline](sample-pipeline.md) for the GPU-compute end of that loop with concrete cell-by-cell output, and [Getting Started](getting-started.md) for the full skill index.
