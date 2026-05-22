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

If `gh` itself isn't installed:

- **macOS:** `brew install gh`
- **Linux (Debian/Ubuntu):** `sudo apt install gh` (newer distros) or follow [cli.github.com/manual/installation](https://cli.github.com/manual/installation) for the official apt repo
- **Linux (Fedora/RHEL):** `sudo dnf install gh`
- **Windows:** `winget install --id GitHub.cli` or `choco install gh`
- **Any OS:** download a release from [github.com/cli/cli/releases](https://github.com/cli/cli/releases)

If installed but not logged in: `gh auth login` (pick HTTPS, paste a token with `repo` + `project` + `workflow` scopes).

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

You have a goal but no plan. Ask Claude to propose 3–5 distinct angles of attack against issue #1, each one concrete enough to become its own hypothesis sub-issue. Each strategy should come with a falsifiability check (what would kill it) and a rough work estimate so you can prioritize.

**Input (in Claude)**

```
Read memory/index.md, the new findings, and the open questions. Then
propose 3-5 distinct strategies to make progress on issue #1. For each:
- One-line hypothesis
- What evidence would confirm or kill it
- Roughly how much work (small / medium / large)
- Whether it needs GPU compute

Don't open issues yet — print the list and wait for me to pick which
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

[C] Ablation on the architectural choice the paper hand-waves
    Confirm: ablation shows the choice matters (>2σ)
    Kill:    ablation shows it's interchangeable with simpler variant
    Work:    large · GPU: yes

[D] Pure-analysis pass on Section 4's math
    Confirm: derivation holds; assumptions are stated
    Kill:    find a hidden assumption that limits scope
    Work:    small · GPU: no

Greenlight which to spawn?
```

Reply with something like *"greenlight A, B, D — skip the GPU-heavy ablation for now"*. Claude then opens one sub-issue per greenlit strategy (label: `hypothesis`, linked to issue #1) and adds each to the project board's Backlog column.

> **Why falsifiability?** The "Kill:" line is the FUNGI counter-argument pattern from CLAUDE.md — every finding and theme must answer *"what would disprove this?"* to resist confirmation bias. Asking the same question of strategies before they become work prevents you from spending a week on a hypothesis you can't actually falsify.

---

## Step 6 — Spawn the agent team

For each greenlit hypothesis, spin up a parallel agent in its own git worktree. They share `memory/` and `sources/` (both at HEAD when the worktree is created) but write to isolated branches, so they don't step on each other's commits.

**Input (in Claude)**

```
For each open hypothesis sub-issue under #1, spawn an Agent with
isolation: "worktree". Each agent gets:
- The parent goal (from #1)
- Its specific hypothesis angle (from its sub-issue body)
- Branch: hypothesis/GH-<sub-issue>-<slug>
- Instructions to follow CLAUDE.md conventions, work in memory/,
  commit + push when done, then comment on its sub-issue with a
  one-paragraph summary + links to the memory pages it created

Dispatch all of them in parallel — they're independent.
```

**Output (expected shape)**

```
Dispatching 3 hypothesis agents in parallel:

[A] hypothesis/GH-2-replicate-baseline    worktree → .worktrees/gh-2 …  RUNNING
[B] hypothesis/GH-3-stress-test-claim     worktree → .worktrees/gh-3 …  RUNNING
[D] hypothesis/GH-5-section-4-math        worktree → .worktrees/gh-5 …  RUNNING

I'll report back as each finishes. You can keep working on main in
the meantime — their changes won't appear here until they push and
you pull.
```

### What each agent does

Inside its worktree, an agent independently:

1. Reads `CLAUDE.md`, the parent goal, and its sub-issue body
2. Reads relevant `memory/` pages (findings, open questions for its angle)
3. Does the work — analysis, ingest more sources, run code, etc.
4. Writes new findings under `memory/findings/` (one file per finding)
5. Updates `memory/index.md` and appends to `memory/log.md`
6. Commits to its `hypothesis/GH-<id>-<slug>` branch and pushes
7. Comments on its sub-issue with a summary + links

### When agents finish

You'll see something like:

```
[A] hypothesis/GH-2-replicate-baseline    DONE   3 new findings, 1 contradiction flagged
[B] hypothesis/GH-3-stress-test-claim     DONE   2 findings (1 negative), open question added
[D] hypothesis/GH-5-section-4-math        DONE   1 finding, math reproduces cleanly
```

From here:

- **Contradictions across branches?** → `/synthesize` to merge findings, surface conflicts in `memory/open-questions/`
- **One hypothesis looks shaky?** → `/critique` against just that branch
- **Need experiments / GPU?** → see Step 7 below and `/vastai`

> **Coordination is async, not chatty.** Agents don't talk to each other; they all push to GitHub and the next sync pass picks up everything. The `synthesis/` branch (per CLAUDE.md's git flow) is where you reconcile what they produced.

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

---

## Step 7 — Set up Python + Vast.ai (optional, only if a hypothesis needs a GPU)

Skip this step if all your greenlit hypotheses are pure-analysis. The moment one of them needs GPU compute (training, big inference, profiling), you'll want the Python env and the `vastai` CLI ready in this repo so the `/vastai` skill works.

Ask Claude to set both up in one turn — no need to run the commands yourself.

**Input (in Claude)**

```
Set up the Python env and the vastai CLI in this repo:
1. Run `uv sync` to create .venv from pyproject.toml
2. Add the vastai CLI as a dependency: `uv add vastai`
3. Verify: `uv run vastai --version` prints a version
4. Walk me through the `/vastai` skill's setup checks (API key + SSH
   key) and stop before actually renting anything
```

**Output (expected shape)**

```
Running `uv sync` …
  Resolved 47 packages in 412ms
  Installed 47 packages in 1.8s

Running `uv add vastai` …
  Added `vastai>=0.3.0` to pyproject.toml
  Installed in .venv

Running `uv run vastai --version` …
  vastai 0.3.x

/vastai setup checks:
  ✓ vastai CLI installed
  ✗ API key — not found at ~/.vast_api_key
    → Visit https://cloud.vast.ai/account/, copy your API key,
      then run: vastai set api-key <KEY>
  ✗ SSH key — no key registered with your Vast.ai account
    → Pick one:
       A) vastai create ssh-key                  (auto-generates)
       B) vastai create ssh-key --ssh-key "$(cat ~/.ssh/id_ed25519.pub)"

Stopping before rent. Run `/vastai rent` when you're ready to spin up
a GPU.
```

Once API key + SSH key are sorted, `/vastai rent` (covered in the [Sample Pipeline](sample-pipeline.md) walkthrough) takes over from here.
