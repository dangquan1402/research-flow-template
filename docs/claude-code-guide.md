---
layout: default
title: Claude Code Guide
nav_order: 4
---

# Claude Code Setup Guide
{: .no_toc }

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

This document explains every Claude Code primitive used in this repo: what each concept is, why it exists here, and how the pieces fit together. Read this before touching `.claude/`.

---

## Table of Contents

1. [What is Claude Code?](#what-is-claude-code)
2. [CLAUDE.md — The Brain](#claudemd--the-brain)
3. [`.claude/` Folder Layout](#claude-folder-layout)
4. [settings.json — Hook Wiring](#settingsjson--hook-wiring)
5. [Hooks — Automated Guardrails](#hooks--automated-guardrails)
6. [Skills — Custom Slash Commands](#skills--custom-slash-commands)
7. [Repo Folder Layout](#repo-folder-layout)
8. [How It All Fits Together](#how-it-all-fits-together)

---

## What is Claude Code?

Claude Code is Anthropic's CLI that gives an AI agent persistent access to your terminal, files, and tools. Unlike a chat window, Claude Code:

- Reads and writes files directly
- Runs shell commands on your behalf
- Persists context across sessions via files (CLAUDE.md, memory/)
- Can be given custom commands (skills) and automated rules (hooks)

When you run `claude` in this repo, it loads the configuration from `.claude/` and CLAUDE.md before doing anything else.

---

## CLAUDE.md — The Brain

`CLAUDE.md` is the primary instruction file. Claude Code reads it automatically at startup for every session in this directory. Think of it as the persistent system prompt for this project.

**What it contains in this repo:**
- The research loop definition (what `/research`, `/analyze`, etc. are supposed to do)
- Memory structure rules (what goes where, what frontmatter is required)
- Git branch conventions
- Quality standards (FUNGI counter-arguments, verification gates, confidence levels)
- Experiment workflow and failure classification

**Rule:** Everything that Claude must always know or always follow belongs in CLAUDE.md. Things that are step-by-step procedures for specific commands belong in skills.

**Hierarchy:** If CLAUDE.md and a skill disagree, CLAUDE.md wins — it's always in context. Skills are only loaded when invoked.

---

## `.claude/` Folder Layout

```
.claude/
├── settings.json        # Hook wiring — which scripts fire on which events
├── hooks/
│   ├── block-source-modification.sh   # PreToolUse: reject edits to sources/
│   ├── block-commit-protected-branch.sh  # PreToolUse: reject git commit on main
│   └── post-memory-update.sh          # PostToolUse: remind to update index/log
└── skills/
    ├── research.md      # /research skill
    ├── analyze.md       # /analyze skill
    ├── synthesize.md    # /synthesize skill
    ├── experiment.md    # /experiment skill
    ├── distill.md       # /distill skill
    ├── evidence.md      # /evidence skill
    ├── verify.md        # /verify skill
    ├── examples.md      # /examples skill
    ├── critique.md      # /critique skill
    ├── lint.md          # /lint skill
    └── read-pdf/        # /read-pdf skill (has helper scripts)
        ├── SKILL.md
        └── scripts/pdf_to_images.py
```

---

## settings.json — Hook Wiring

`settings.json` tells Claude Code which shell scripts to run and when. It does **not** contain the logic — that lives in the hook scripts. This file is just the routing table.

```json
{
  "hooks": {
    "PreToolUse": [...],   // runs BEFORE a tool executes
    "PostToolUse": [...]   // runs AFTER a tool executes
  }
}
```

Each entry has a `matcher` (which tool to intercept) and a `command` (what to run).

**Available hook events:**

| Event | When it fires | Typical use |
|---|---|---|
| `PreToolUse` | Before Claude calls a tool | Block dangerous operations |
| `PostToolUse` | After Claude calls a tool | Trigger reminders or side effects |
| `SessionStart` | When a Claude Code session begins | Greet, run checks |
| `UserPromptSubmit` | When the user submits a message | Validate or augment input |
| `PreCompact` | Before context is compacted | Save state |

**How matchers work:**

The `matcher` field is matched against the tool name. Use `|` for OR:

```json
{ "matcher": "Edit|Write", ... }   // fires for Edit or Write
{ "matcher": "Bash", ... }         // fires only for Bash
{ "matcher": "Edit", ... }         // fires only for Edit
```

**Environment variables passed to hooks:**

Hooks receive context via environment variables in the command string:

| Variable | Meaning |
|---|---|
| `$TOOL_NAME` | Name of the tool being called (`Edit`, `Bash`, etc.) |
| `$TOOL_INPUT_FILE_PATH` | File path argument (for Edit/Write) |
| `$TOOL_INPUT_COMMAND` | Shell command (for Bash) |

**Exit codes control behavior:**

| Exit code | Effect |
|---|---|
| `0` | Allow the tool to proceed |
| `1` | Non-blocking error — execution continues, Claude sees stdout as context |
| `2` | **Block** the tool — Claude sees the script's stderr as the error message |

This is how hooks enforce rules: they print a human-readable message to **stderr** and `exit 2`.

---

## Hooks — Automated Guardrails

This repo uses three hooks that encode hard invariants from CLAUDE.md.

### `block-source-modification.sh` (PreToolUse → Edit)

**What:** Rejects any `Edit` call targeting a file under `sources/`.

**Why:** Sources are the raw material of research. Once ingested, they must never change — otherwise findings that cite them become untrustworthy. If Claude wants to "fix" a source, it should create a finding in `memory/findings/` instead.

**How:** Checks if `$TOOL_INPUT_FILE_PATH` contains `sources/` and exits 2 if so.

```bash
if [[ "$FILE_PATH" == *"sources/"* && "$FILE_PATH" != *".gitkeep"* ]]; then
  echo "BLOCKED: Source files are immutable..." >&2
  exit 2
fi
```

Note: `Write` is not blocked — only `Edit`. The `Write` tool creates new files; `Edit` modifies existing ones. New source files are allowed; modifying existing ones is not.

---

### `block-commit-protected-branch.sh` (PreToolUse → Bash)

**What:** Rejects `git commit` commands when on the `main` branch.

**Why:** All research work happens on typed branches (`research/`, `hypothesis/`, `synthesis/`, `review/`). Committing to main directly bypasses the issue-tracking and review workflow. The hook enforces this automatically rather than relying on Claude remembering the rule.

**How:** Parses `$TOOL_INPUT_COMMAND` for `git commit`, then checks `git rev-parse --abbrev-ref HEAD`. If the branch is `main`, it exits 2.

```bash
if [[ "$COMMAND" == *"git commit"* ]]; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [[ "$BRANCH" == "main" ]]; then
    echo "BLOCKED: Cannot commit directly to main..." >&2
    exit 2
  fi
fi
```

---

### `post-memory-update.sh` (PostToolUse → Edit|Write)

**What:** After any file write inside `memory/`, prints a reminder to update `memory/index.md` and append to `memory/log.md`.

**Why:** The index and log are the consistency layer for working memory. Without them, memory pages become orphans (not findable) or operations go unrecorded. This hook ensures Claude doesn't forget to do both in the same turn.

**How:** Checks if the modified file is under `memory/`, excluding the index/log/registry themselves (which don't need reminders when they're the ones being updated).

```bash
if [[ "$FILE_PATH" == *"memory/"* && "$FILE_PATH" != *"memory/index.md"* ... ]]; then
  echo "REMINDER: memory/ was modified. Update memory/index.md and append to memory/log.md."
fi
```

This is a PostToolUse hook with exit code 0 — it doesn't block anything, just prints a reminder that Claude Code will see and act on.

---

## Skills — Custom Slash Commands

Skills are markdown files that define what Claude should do when you type `/skill-name`. They live in `.claude/skills/` and are loaded on-demand (not at startup).

**Invoking a skill:** Type `/research`, `/analyze`, `/synthesize`, etc. in the Claude Code prompt. Claude Code finds the matching skill file and follows its instructions.

**Skill file format:**

```markdown
---
name: research
description: Short description shown in skill picker
user_invocable: true
---

# /research — Start a New Research Goal

## Gather Information
...

## Workflow
...
```

The YAML frontmatter tells Claude Code the skill name and whether users can invoke it directly. The body is a prompt Claude follows when the skill is activated.

**Skills in this repo:**

| Skill | Purpose |
|---|---|
| `/research` | Define a new research goal, create GitHub issue, branch, goal file |
| `/analyze` | Ingest a source (URL/file/topic), extract findings and entities, update memory |
| `/synthesize` | Consolidate findings into themes, resolve contradictions, produce output |
| `/experiment` | Design hypothesis, run experiment code, classify results, write finding |
| `/distill` | Extract decisions from settled findings into `memory/decisions/` |
| `/evidence` | Generate charts/tables/plots backing key claims → `outputs/evidence/` |
| `/verify` | Write code to check claims programmatically → `outputs/verification/` |
| `/examples` | Create worked examples illustrating findings → `outputs/examples/` |
| `/critique` | Adversarial review with gap analysis and honest write-up → `outputs/critiques/` |
| `/lint` | Health-check memory: orphans, contradictions, staleness, missing cross-refs |
| `/read-pdf` | Render a PDF to images page-by-page and read them (preserves figures/tables) |
| `/import` | Bulk-import an existing project — copies artifacts to `sources/`, extracts findings + entities, scaffolds memory in one pass |
| `/vastai` | Rent and manage GPU instances on Vast.ai (rent, ssh, jupyter, sync, terminate). State tracked per-project in `experiments/.vastai-instance.json` |

**Skills vs CLAUDE.md:**

CLAUDE.md describes the *what* and *why* of the research system. Skills describe the *how* for specific operations — the step-by-step procedure. When you invoke `/analyze`, Claude follows the skill's workflow; CLAUDE.md's memory rules govern what the output should look like.

---

## Repo Folder Layout

```
research-flow-template/
├── CLAUDE.md                  # Project instructions — always loaded
├── .claude/                   # Claude Code config (hooks, skills, settings)
├── .github/ISSUE_TEMPLATE/    # GitHub issue templates for research-goal, hypothesis, finding
│
├── sources/                   # Immutable raw material (never edited after creation)
├── memory/                    # LLM-maintained working memory
│   ├── index.md               # Catalog of all pages — kept up to date every cycle
│   ├── log.md                 # Append-only operation log
│   ├── entity-registry.json   # Dedup index — checked before creating entity pages
│   ├── entities/              # People, orgs, concepts, tools
│   ├── findings/              # Discrete insights with citations and confidence
│   ├── themes/                # Cross-cutting patterns across findings
│   ├── open-questions/        # Gaps to investigate
│   └── decisions/             # Distilled actionable decisions
│
├── goals/                     # Active research goal definitions
├── outputs/                   # Deliverables (reports, evidence, verification, examples, critiques)
│   ├── evidence/
│   ├── verification/
│   ├── examples/
│   └── critiques/
│
├── experiments/               # Blank scaffold — add your own training code
│   ├── configs/baselines/     # Baseline configs (user-defined)
│   ├── configs/sweeps/        # Sweep configs (user-defined)
│   └── results/               # run-log.jsonl + result files
│
└── docs/                      # Human-readable documentation
    ├── claude-code-guide.md   # This file
    ├── git-workflow.md        # Branch strategy and multi-agent dispatch
    └── memory-page-template.md # Frontmatter templates for memory pages
```

**The three-layer memory model (from Karpathy's LLM Wiki pattern):**

1. **Sources** (`sources/`) — immutable raw material. Write-once, never edited.
2. **Working Memory** (`memory/`) — LLM-maintained wiki. Updated every research cycle.
3. **Schema** (CLAUDE.md) — conventions and rules. Read by Claude every session.

---

## How It All Fits Together

Here's what happens end-to-end when you start a research session:

1. **You run `claude` in the repo root.**
   Claude Code loads `CLAUDE.md` and `.claude/settings.json` automatically.

2. **You type `/research`.**
   Claude Code finds `.claude/skills/research.md` and follows its workflow: asks for your goal, creates a GitHub issue, creates a branch, writes a goal file, logs the operation.

3. **You type `/analyze https://some-paper.pdf`.**
   Claude fetches/reads the source, extracts entities and findings into `memory/`, and calls `Edit` or `Write` on those files.

4. **The `post-memory-update.sh` hook fires** (PostToolUse → Edit).
   It prints a reminder to update `memory/index.md` and append to `memory/log.md`. Claude does this in the same turn.

5. **If Claude tries to edit a file in `sources/`**, the `block-source-modification.sh` hook fires and blocks it with an error message.

6. **If Claude tries `git commit` while on `main`**, the `block-commit-protected-branch.sh` hook blocks it.

7. **You type `/synthesize`.** Claude reads all of `memory/findings/`, builds themes, resolves contradictions, writes an output report.

8. **You type `/evidence`.** Claude generates charts and plots to `outputs/evidence/`.

9. **At any point**, you can spawn parallel agents on separate hypothesis branches using the `Agent` tool with `isolation: "worktree"` — each agent gets its own checkout of the repo, works independently, and pushes its branch when done.

---

## Adding Your Own Hooks

To add a new hook:

1. Write a shell script in `.claude/hooks/`. Exit 0 to allow, exit 2 to block (message to stderr). Exit 1 is non-blocking.
2. Register it in `.claude/settings.json` under the appropriate event and matcher.

Example — block writing to `outputs/` directly (require it to go through a skill):

```bash
# .claude/hooks/block-direct-output-write.sh
if [[ "$FILE_PATH" == *"outputs/"* ]]; then
  echo "BLOCKED: Use /evidence, /verify, /examples, or /critique to produce outputs." >&2
  exit 2
fi
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "bash .claude/hooks/block-direct-output-write.sh Write \"$TOOL_INPUT_FILE_PATH\"" }]
      }
    ]
  }
}
```

---

## Adding Your Own Skills

To add a new skill:

1. Create `.claude/skills/my-skill.md` with YAML frontmatter (`name`, `description`, `user_invocable: true`) and a markdown body describing the workflow.
2. Invoke it with `/my-skill` in the Claude Code prompt.

Skills can reference CLAUDE.md conventions freely — Claude has CLAUDE.md in context when a skill runs.
