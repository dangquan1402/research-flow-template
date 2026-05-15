---
layout: default
title: Getting Started
nav_order: 3
---

# Getting Started
{: .no_toc }

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## Prerequisites

### Required

**Claude Code** — the AI agent that drives everything.
```bash
npm install -g @anthropic-ai/claude-code
claude   # opens browser login on first run (Claude.ai Pro or Max)
```

**Node.js ≥ 18** — needed for `npx create-research-flow`.
```bash
node --version   # should print v18+
```

**Python ≥ 3.11 + uv** — for the Python toolchain and PDF skill.
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**GitHub CLI** — creates the repo, Project board, labels, and branch–issue links.
```bash
brew install gh && gh auth login
```

### Optional

**Your ML framework** — `experiments/` is a blank scaffold. Add whatever you need:
```bash
uv add torch        # or jax, tensorflow, scikit-learn, etc.
```

---

## Scaffold a New Project

```bash
npx create-research-flow my-project
```

The CLI will:
- Clone this template into `my-project/`
- Create a GitHub repo + Project board under your account
- Seed labels (`research-goal`, `hypothesis`, `finding`, `synthesis`, `maintenance`)
- Set up board columns (`Backlog | In Progress | Synthesizing | Done`)
- Run `uv sync` to install core deps
- Launch `claude`

---

## Your First Research Session

Once inside Claude Code:

### 1. Define your goal

```
/research
```

Claude will ask for your research question, then:
- Open a GitHub issue (label: `research-goal`)
- Create a `research/GH-{n}-{slug}` branch
- Write a goal file in `goals/`
- Log the operation to `memory/log.md`

### 2. Feed in sources

```
/analyze https://arxiv.org/abs/...
/analyze path/to/paper.pdf
/analyze "topic: transformer attention mechanisms"
```

Each call extracts entities and findings into `memory/`, updates `memory/index.md`, and logs the operation.

For PDFs with figures and tables, use the image-based reader:
```
/read-pdf path/to/paper.pdf
```

### 3. Import an existing project

```
/import path/to/existing-repo
/import https://github.com/org/repo
```

Bulk-copies artifacts to `sources/`, extracts findings and entities in one pass.

### 4. Run experiments

```
/experiment
```

Claude will ask for your hypothesis and acceptance criteria, then guide you through writing an experiment plan, running your code, classifying the result, and writing a finding.

### 5. Synthesize

```
/synthesize
```

Reads all of `memory/findings/`, builds themes, resolves contradictions, and writes an output report to `outputs/`.

### 6. Distill decisions

```
/distill
```

Extracts actionable decisions from settled findings into `memory/decisions/`.

---

## Parallel Research with Multiple Agents

Spin up agents on separate `hypothesis/` branches to explore different angles simultaneously:

```
Agent({
  isolation: "worktree",
  prompt: "Research goal: {goal}. Your angle: {angle}. Branch: hypothesis/GH-{n}-{slug}.",
  description: "Hypothesis: {angle}"
})
```

Each agent works in its own git worktree — no conflicts. Merge the best findings via a `synthesis/` branch.

---

## Useful Commands

| Command | Purpose |
|---|---|
| `uv sync` | Install core deps |
| `uv add <pkg>` | Add a dependency |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run pre-commit run --all-files` | Run all pre-commit hooks |
