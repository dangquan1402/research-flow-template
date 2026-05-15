---
layout: default
title: Claude Code Quick Start
nav_order: 2
---

# Claude Code Quick Start (for researchers)
{: .no_toc }

This page is for researchers — PhD students, postdocs, RSEs — who've never used Claude Code. It introduces the vocabulary first (mapped to lab-and-paper concepts you already know), then gets you to a working session.

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## What is Claude Code?

Claude Code is Anthropic's **CLI research assistant**. It runs in your terminal, reads and writes files in your project directly, runs shell commands (git, tests, training scripts), and remembers your conventions across sessions via plain-text files. Think of it as a postdoc that never leaves the lab and reads every paper you point at — but only knows what's in the files you give it.

Unlike a chat window:
- **Persistent.** State lives in files (`CLAUDE.md`, `memory/`) — survives restarts.
- **Agentic.** It writes code, runs experiments, commits to git, opens issues.
- **Extensible.** You give it custom protocols (skills), safety interlocks (hooks), and parallel assistants (subagents).

---

## Terminology — research translation

Claude Code has its own jargon. Here's the mapping a researcher actually needs:

| Claude Code term | Research-lab equivalent |
|---|---|
| **`CLAUDE.md`** | The *Methods* section of your project. Standing instructions every collaborator (including Claude) reads before touching anything. Conventions, units, file layout, "do not edit X." |
| **Skill** (`/research`, `/analyze`, ...) | A **standardized protocol / SOP.** Invoked the same way each time, produces a structured output. Lives as a markdown file in `.claude/skills/`. |
| **Slash command** | The verb you type to *invoke* a protocol: `/analyze paper.pdf`. |
| **Memory** (`memory/`) | Your **lab notebook**. Findings, entities, open questions, themes. Has an index (`memory/index.md`) — the table of contents — and a log (`memory/log.md`) — the chronological journal. |
| **Sources** (`sources/`) | The **primary literature & raw data** you've collected. Immutable. You annotate; you don't rewrite. |
| **Hook** (Pre/Post) | A **lab safety interlock / cleanup routine.** Auto-fires before or after Claude does something. Used to block bad actions or auto-log good ones. |
| **Permission mode** | **Supervision level.** Default = "ask the PI before each action." `acceptEdits` = "trusted postdoc." `plan` = "read-only literature review." |
| **Subagent / `Agent` tool** | A **parallel grad student.** Spawn one per hypothesis; each gets its own git worktree (its own bench). Merge findings later. |
| **Plugin** | A **packaged toolkit** — a bundle of skills + hooks + agents. Like a reagent kit you import wholesale. |
| **Marketplace** | A **protocol repository** (`protocols.io` for AI workflows). Browse, install, run peer-reviewed plugins. |
| **MCP server** | An **external instrument feed.** Exposes data from another system (a database, Jira, a browser, your LIMS) to Claude in a standard way. |
| **Context window** | The **working bench space.** Long sessions clutter it — `/compact` summarizes, `/clear` wipes it down. |

---

## 1. Install

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

Requires Node.js 18+. Official docs: [Setup](https://docs.claude.com/en/docs/claude-code/setup) · [Quickstart](https://docs.claude.com/en/docs/claude-code/quickstart).

---

## 2. Log in

```bash
claude       # first run opens browser
```

Authenticate with **Claude.ai Pro / Max** (flat fee, recommended for daily use) or an **Anthropic API key** (pay-per-token, better for headless / CI).

---

## 3. Your first session

```bash
cd path/to/your/project
claude
> what does this project do?
```

Claude reads files and answers. It asks permission before editing or running shell commands. Exit with `Ctrl+C` twice or `/exit`.

---

## 4. Built-in slash commands (the ones you'll actually use)

Type `/` to see them all.

| Command | What it does | When you need it |
|---|---|---|
| `/help` | List commands and shortcuts | First few sessions |
| `/init` | Generate a starter `CLAUDE.md` | Brand-new repo |
| `/clear` | Wipe conversation context | Switching tasks |
| `/compact` | Summarize conversation, keep key facts | Long sessions |
| `/context` | Show what's in the context window | Debugging "why doesn't it remember?" |
| `/resume` | Reopen a past session | Continuing yesterday's work |
| `/model` | Switch model (Opus / Sonnet / Haiku) | Cost vs. quality tradeoff |
| `/cost` | Show token usage and cost | Budget watch |
| `/memory` | View / edit `CLAUDE.md` files | Tweaking project rules |
| `/plugin` | Browse / install plugins from marketplaces | Adding capabilities |
| `/exit` | Quit | — |

Custom skills (this repo's `/research`, `/analyze`, `/synthesize`, etc.) appear in the same list.

Official reference: [Slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands) · [CLI reference](https://docs.claude.com/en/docs/claude-code/cli-reference).

---

## 5. Keyboard shortcuts

| Key | Action |
|---|---|
| `Shift+Tab` | Cycle permission modes (default → acceptEdits → plan) |
| `Esc` | Interrupt Claude mid-action |
| `Esc Esc` | Rewind to a previous message |
| `Ctrl+R` | Toggle verbose / tool-call view |
| `#` at line start | Save the rest of the line to `CLAUDE.md` as a rule |
| `!` at line start | Run the rest of the line as a shell command |
| `@` | Reference a file path (autocompletes) |

Official reference: [Interactive mode](https://docs.claude.com/en/docs/claude-code/interactive-mode).

---

## 6. Memory — Claude's lab notebook

Memory is **all the state Claude carries between sessions**, and it's all just files you can read and edit yourself. Three layers:

### `CLAUDE.md` — standing methods
Plain markdown in your repo root, auto-loaded every session. Put:
- Project conventions (style, units, file naming, lint rules)
- Architecture overview ("inputs go here, outputs go there")
- Don't-do rules ("never edit `sources/`")
- Useful commands (test, build, deploy)

Generate a starter with `/init`. Append a rule mid-session with `#`:
```
> # ALL plots must include error bars and a caption with N
```
Claude writes that to `CLAUDE.md` so it persists.

There are **three levels** of `CLAUDE.md`, in increasing specificity:
1. `~/.claude/CLAUDE.md` — user-global (your personal preferences across every project)
2. `<repo>/CLAUDE.md` — project-wide (shared with collaborators via git)
3. `<subdir>/CLAUDE.md` — directory-local (e.g. one set of rules for `experiments/`)

### `memory/` — working notes (this template only)
Not built into Claude Code itself, but a convention this template uses. A wiki-style folder Claude maintains:
- `memory/index.md` — table of contents
- `memory/log.md` — append-only chronological journal
- `memory/findings/` — discrete insights with citations and confidence
- `memory/entities/` — people, papers, concepts, tools
- `memory/themes/` — cross-cutting patterns
- `memory/open-questions/` — gaps queued for experiments

See [Claude Code Guide](claude-code-guide) for the structural rules this template enforces.

### Session memory (`/resume`)
Each chat session is checkpointed automatically. `/resume` reopens any past session with full history — useful when you stop work mid-experiment.

Official reference: [Memory management](https://docs.claude.com/en/docs/claude-code/memory) · [Manage sessions](https://docs.claude.com/en/docs/claude-code/sessions).

---

## 7. Hooks — pre & post interlocks

Hooks are **shell scripts that fire automatically before or after Claude calls a tool.** They live in `.claude/hooks/`, wired up by `.claude/settings.json`. Think pre-flight checklist + post-experiment cleanup.

Two events you'll use 95% of the time:

### `PreToolUse` — safety interlock (fires *before*)
Runs before Claude executes a tool. Can **block** the action by exiting `2` and writing an error to stderr. Examples:

| Hook | Lab analogy |
|---|---|
| Block `Edit` on anything in `sources/` | "Primary data is read-only. Annotate in your notebook instead." |
| Block `git commit` while on `main` | "Don't commit directly to the protocol of record — work on a branch." |
| Block `Bash` containing `rm -rf` on production paths | Fume-hood interlock |

This template ships two:
- `.claude/hooks/block-source-modification.sh` — protects `sources/` immutability
- `.claude/hooks/block-commit-protected-branch.sh` — forces typed branches

### `PostToolUse` — cleanup / journaling (fires *after*)
Runs after the tool succeeds. Cannot block — used for side effects: reminders, auto-formatting, logging.

| Hook | Lab analogy |
|---|---|
| After an `Edit` in `memory/`, remind Claude to update `memory/index.md` and `memory/log.md` | "Wrote a new entry? Update the TOC and date-stamp it." |
| Auto-run `ruff format` after `Write` | Auto-tidy bench |
| Append a row to `experiments/results/run-log.jsonl` after a run | Automatic instrument journal |

This template ships:
- `.claude/hooks/post-memory-update.sh` — reminds to update index + log after `memory/` writes

### Wiring (the routing table)
`.claude/settings.json` is the wiring — *which* script fires on *which* event for *which* tool:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "bash .claude/hooks/block-source-modification.sh ..." }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "bash .claude/hooks/post-memory-update.sh ..." }]
      }
    ]
  }
}
```

| Exit code | Effect |
|---|---|
| `0` | Allow. Output to stdout becomes context Claude can see. |
| `1` | Non-blocking warning. |
| `2` | **Block.** stderr is shown to Claude as the rejection reason. |

Other hook events exist (`SessionStart`, `UserPromptSubmit`, `PreCompact`) — see [Claude Code Guide](claude-code-guide) for the full list.

Official reference: [Hooks guide](https://docs.claude.com/en/docs/claude-code/hooks-guide) · [Hooks reference](https://docs.claude.com/en/docs/claude-code/hooks).

---

## 8. Plugins & the marketplace

A **plugin** is a packaged bundle of skills + hooks + agents + commands. A **marketplace** is a registry you can browse and install from.

### Browse and install
Inside Claude:
```
/plugin
```
Opens an interactive UI to add marketplaces and install plugins.

Or directly:
```
/plugin marketplace add anthropics/claude-code     # add Anthropic's official marketplace
/plugin install pr-review-toolkit@claude-code      # install a specific plugin
```

Install scopes (where the settings go):
- `--scope user` (default) — your account, all projects
- `--scope project` — checked into the repo, shared with the team
- `--scope local` — this checkout only, gitignored

### Useful plugins for researchers
The official marketplace at `anthropics/claude-code` includes:
- **pr-review-toolkit** — structured PR review (good for reviewing student / collaborator commits)
- **code-review** — runs `gh` CLI against PRs
- **plugin-dev** — for building your own plugins
- **agent-sdk-dev** — for building Python/TS agents

Community marketplaces (browse via `/plugin marketplace add <github-repo>`) ship things like dataset-loader skills, paper-summarization skills, LaTeX helpers, and lab-notebook scaffolds.

### Make your own
Anything in `.claude/skills/`, `.claude/hooks/`, and `.claude/agents/` of this repo *is* effectively a plugin. To publish, restructure into a plugin layout (see `claude-plugin-marketplace` template) and push to a GitHub repo. Then others install with `/plugin install your-plugin@your-org/your-repo`.

Official reference: [Plugins](https://docs.claude.com/en/docs/claude-code/plugins) · [Plugin marketplaces](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces) · [Plugins reference](https://docs.claude.com/en/docs/claude-code/plugins-reference) · [Anthropic's official marketplace](https://github.com/anthropics/claude-code/tree/main/plugins).

---

## 9. Permission modes

Four supervision levels that control how aggressively Claude can act without asking.

| Mode | Behavior | Research analogy |
|---|---|---|
| `default` | Ask before every edit / shell command | PI-supervised, first-rotation student |
| `acceptEdits` | Auto-approve file edits, still ask for shell | Trusted postdoc on a familiar task |
| `plan` | **Read-only.** Investigates and proposes a plan, never writes or executes | Literature review / protocol design session |
| `bypassPermissions` | Auto-approve **everything** — no prompts at all (⚠️) | Sandboxed automation only |

### Plan mode — read-only research

This is the one researchers underuse. In `plan` mode Claude **cannot** edit files, run shell commands, or make any state-changing tool call. It can only `Read`, `Grep`, `Glob`, search the web, and reason. At the end it presents a written plan and waits for you to approve before doing anything destructive.

Use plan mode when you want to:
- Survey an unfamiliar codebase before letting Claude touch it
- Have Claude **design an experiment** without immediately running it
- Get a literature-review-style answer with citations, no side effects
- Audit "what would Claude actually do if I asked it to refactor X?" — safely
- Onboard a new project — let Claude draft a `CLAUDE.md` proposal, then you approve

Plan mode treats your repo the way a careful researcher treats primary sources: look, take notes, propose — never overwrite.

### How to switch — three ways

**1. Live, mid-session (most common):** press `Shift+Tab` to cycle through modes. The current mode is shown in the status line.

```
default  →  Shift+Tab  →  acceptEdits  →  Shift+Tab  →  plan  →  Shift+Tab  →  default
```

**2. At startup:** pass `--permission-mode` on the command line.

```bash
claude --permission-mode plan              # safe exploration session
claude --permission-mode acceptEdits       # trusted day-to-day
claude --permission-mode bypassPermissions # ⚠️ no prompts at all
```

**3. Persistent default:** set it in `.claude/settings.json` (project) or `~/.claude/settings.json` (user-global):

```json
{
  "permissions": {
    "defaultMode": "acceptEdits"
  }
}
```

### About `bypassPermissions`

There's also a shorthand flag:
```bash
claude --dangerously-skip-permissions   # equivalent to --permission-mode bypassPermissions
```

This **really does** skip every prompt — Claude can `rm -rf`, force-push, delete branches, install packages, exfiltrate via curl, anything. Only use it inside:
- An ephemeral Docker container
- A disposable cloud VM / Codespace
- A scratch worktree you don't mind losing

**Never** run `bypassPermissions` in your real project checkout, your home directory, or anywhere with credentials in env vars. The friction of permission prompts is the safety net for the times you didn't realize what you were asking for.

Official reference: [Permission modes](https://docs.claude.com/en/docs/claude-code/iam#permission-modes) · [IAM overview](https://docs.claude.com/en/docs/claude-code/iam).

---

## 10. Headless mode — for batch jobs and CI

```bash
claude -p "summarize the last 5 commits"
claude -p "run /lint and report contradictions" --permission-mode acceptEdits
```

Pipe into anything. Good for cron jobs, CI quality gates, automated weekly synthesis runs.

Official reference: [Headless mode (`-p` / SDK)](https://docs.claude.com/en/docs/claude-code/sdk).

---

## 11. Subagents — parallel research

Spin up multiple agents on different angles of the same question. Each gets an isolated git worktree (their own bench), so no merge conflicts during parallel work:

```
Agent({
  isolation: "worktree",
  description: "Hypothesis: attention is a content-based router",
  prompt: "Research goal: ... Your angle: ... Branch: hypothesis/GH-7-attention-routing"
})
```

After they finish, a `synthesis/` branch merges the best findings. See [Git Workflow](git-workflow).

Official reference: [Subagents](https://docs.claude.com/en/docs/claude-code/sub-agents).

---

## 12. Where to go next

- **[Getting Started](getting-started)** — install prerequisites, scaffold a new project, run your first `/research` session
- **[Claude Code Guide](claude-code-guide)** — every primitive used in this repo, in depth
- **[Git Workflow](git-workflow)** — branch types and multi-agent dispatch
- **[Memory Templates](memory-page-template)** — frontmatter reference for memory pages

---

## Common pitfalls (researcher edition)

- **No `CLAUDE.md`** — every session starts naive. Always `/init` early. Treat it like the front matter of your lab notebook.
- **Context bloat in long sessions** — Claude slows down and forgets early decisions. `/compact` (summarize) or `/clear` (wipe) between tasks.
- **Letting Claude edit `sources/`** — defeats reproducibility. The hook blocks `Edit`; if you need to "correct" a source, write a finding instead.
- **Trusting `bypassPermissions`** — it really will run anything. Reserve for disposable containers / sandboxes.
- **Forgetting the index / log** — orphan memory pages are unfindable later. The `post-memory-update.sh` hook reminds you; do it in the same turn.
- **Assuming yesterday's session is loaded** — it isn't unless you `/resume`. Persistent state lives in `CLAUDE.md` and `memory/`, not in the session log.

---

## Official references

All linked above in context — collected here for convenience.

### Getting started
- [Overview](https://docs.claude.com/en/docs/claude-code/overview)
- [Quickstart](https://docs.claude.com/en/docs/claude-code/quickstart)
- [Setup](https://docs.claude.com/en/docs/claude-code/setup)
- [CLI reference](https://docs.claude.com/en/docs/claude-code/cli-reference)
- [Interactive mode (keybindings, shortcuts)](https://docs.claude.com/en/docs/claude-code/interactive-mode)

### Memory & sessions
- [Memory management (`CLAUDE.md`)](https://docs.claude.com/en/docs/claude-code/memory)
- [Manage sessions (`/resume`, `/clear`, `/compact`)](https://docs.claude.com/en/docs/claude-code/sessions)
- [Settings reference (`settings.json`)](https://docs.claude.com/en/docs/claude-code/settings)

### Extending Claude
- [Slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Skills](https://docs.claude.com/en/docs/claude-code/skills)
- [Subagents](https://docs.claude.com/en/docs/claude-code/sub-agents)

### Hooks
- [Hooks guide (with examples)](https://docs.claude.com/en/docs/claude-code/hooks-guide)
- [Hooks reference (all events, exit codes)](https://docs.claude.com/en/docs/claude-code/hooks)

### Plugins & marketplace
- [Plugins](https://docs.claude.com/en/docs/claude-code/plugins)
- [Plugin marketplaces](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces)
- [Plugins reference](https://docs.claude.com/en/docs/claude-code/plugins-reference)
- [Anthropic's official plugin marketplace (GitHub)](https://github.com/anthropics/claude-code/tree/main/plugins)

### Security & automation
- [Permissions / IAM](https://docs.claude.com/en/docs/claude-code/iam)
- [Security best practices](https://docs.claude.com/en/docs/claude-code/security)
- [Headless mode / Agent SDK](https://docs.claude.com/en/docs/claude-code/sdk)
- [MCP servers (external instruments)](https://docs.claude.com/en/docs/claude-code/mcp)

### Community
- [Claude Code GitHub repo](https://github.com/anthropics/claude-code)
- [Awesome Claude Code (curated list)](https://github.com/hesreallyhim/awesome-claude-code)
- [Claude Code docs mirror (fast-search)](https://github.com/ericbuess/claude-code-docs)
