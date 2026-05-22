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

## Step 3 — Drop the PDF in

Move your source PDF into `sources/`, then tell Claude to ingest it. The `/read-pdf` skill renders each page as a PNG so figures, tables, and equations survive — text extraction alone would lose them.

**Input (shell, in another tab or via Claude's bash tool)**

```bash
cp ~/Downloads/my-paper.pdf sources/
```

**Input (in Claude)**

```
/read-pdf sources/my-paper.pdf
```

**Output (expected shape)**

```
Rendering sources/my-paper.pdf → sources/_pdf-images/my-paper/
  page 01 → page-01.png  (1654×2339)
  page 02 → page-02.png
  ...
  page 18 → page-18.png

Loaded 18 pages. Ready to analyze.
```

---

## Step 4 — Ingest: memory + GitHub issue + project board

Now ask Claude to extract findings into memory, open a parent research-goal issue, and add it to the board. The `/analyze` skill drives the memory side; `gh` handles the GitHub side.

**Input (in Claude)**

```
/analyze the PDF I just loaded. Treat it as a fresh research goal.

Do all of this in one pass:
1. Extract entities, findings, and open questions into memory/
2. Update memory/index.md and append a line to memory/log.md
3. Open a parent GitHub issue with label "research-goal" using
   .github/ISSUE_TEMPLATE/research-goal.md
4. Add that issue to the project board (column: Backlog)
5. Print the issue URL and the memory pages you created
```

**Output (expected shape)**

```
Reading 18 pages from sources/_pdf-images/my-paper/ …

Extracted:
  • 6 entities    → memory/entities/{slugs}.md
  • 4 findings    → memory/findings/{slugs}.md
  • 3 open questions → memory/open-questions/{slugs}.md

Updated memory/index.md (+13 entries)
Appended to memory/log.md:
  ## [2026-05-22] ingest | my-paper.pdf → 6 entities, 4 findings

Opened parent issue:
  https://github.com/<you>/my-research/issues/1
  Title: research(my-paper): <goal extracted from abstract>
  Labels: research-goal

Added to project board "my-research" → Backlog
```

> The `block-source-modification` hook will reject any later `Edit` against `sources/` — that's intentional. PDFs are immutable; new insights go in `memory/findings/`.

---

## Step 5 — Brainstorm strategies

You now have a goal but no plan. Ask Claude to propose 3–5 distinct angles of attack, each one concrete enough to become its own hypothesis sub-issue.

**Input (in Claude)**

```
Read memory/index.md, the new findings, and the open questions. Then
propose 3-5 distinct strategies to make progress on issue #1. For each:
- One-line hypothesis
- What evidence would confirm or kill it
- Roughly how much work (small / medium / large)
- Whether it needs GPU compute

Don't open issues yet — just print the list and wait for me to pick which
ones to greenlight.
```

**Output (expected shape)**

```
Strategy candidates for issue #1:

[A] Replicate the paper's baseline on our data
    Confirm: matches reported metric ±5%
    Kill:    diverges by >15% with no obvious config bug
    Work:    medium · GPU: yes

[B] Stress-test the headline claim by varying <X>
    Confirm: claim survives 3+ perturbations
    Kill:    breaks on a single trivial perturbation
    Work:    small · GPU: yes

[C] Compare against the cited prior-work baseline
    Confirm: paper's delta reproduces
    Kill:    prior work matches paper within noise
    Work:    medium · GPU: yes

[D] Ablation on the architectural choice the paper hand-waves
    Confirm: ablation shows the choice matters (>2σ)
    Kill:    ablation shows it's interchangeable with simpler variant
    Work:    large · GPU: yes

[E] Pure-analysis pass on Section 4's math
    Confirm: derivation holds; assumptions are stated
    Kill:    find a hidden assumption that limits scope
    Work:    small · GPU: no

Greenlight which to spawn?
```

You reply with something like *"greenlight A, B, E — skip the GPU-heavy ones for now."* Claude then opens one sub-issue per greenlit strategy (labeled `hypothesis`, linked to issue #1) and adds each to the project board.

---

## Step 6 — Spawn the agent team

For each greenlit hypothesis, spin up a parallel agent in its own git worktree. They share memory but work on isolated branches, so they don't conflict.

**Input (in Claude)**

```
For each open hypothesis sub-issue under #1, spawn an Agent with
isolation: "worktree". Each agent gets:
- The parent goal (from #1)
- Its specific hypothesis angle (from its sub-issue body)
- Branch: hypothesis/GH-<sub-issue>-<slug>
- Instructions to follow CLAUDE.md conventions, work in memory/,
  commit + push when done, then comment on its sub-issue with a summary

Dispatch all of them in parallel — they're independent.
```

**Output (expected shape)**

```
Dispatching 3 hypothesis agents in parallel:

[A] hypothesis/GH-2-replicate-baseline    worktree → .worktrees/gh-2 …  RUNNING
[B] hypothesis/GH-3-stress-test-claim     worktree → .worktrees/gh-3 …  RUNNING
[E] hypothesis/GH-5-section-4-math        worktree → .worktrees/gh-5 …  RUNNING

I'll report back as each one finishes. You can keep working on the main
branch in the meantime — their changes won't show up here until they push
and you pull.
```

When an agent finishes, it pushes its branch, comments on its sub-issue, and Claude surfaces a summary. From there you `/synthesize` to merge findings across branches, or `/critique` an individual hypothesis that looks shaky.

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
