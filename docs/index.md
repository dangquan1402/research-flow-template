---
layout: home
title: Home
nav_order: 1
---

# Research Flow

An agentic research system with persistent working memory. Multiple agents can work in parallel on the same research goal from different angles, with findings compounding in a shared wiki-style memory.

## What is this?

This is a Claude Code template that gives your research project:

- **Persistent memory** — a structured wiki (`memory/`) that survives between sessions
- **Automated guardrails** — hooks that enforce source immutability and branch discipline
- **Slash commands** — skills like `/research`, `/analyze`, `/synthesize` that drive the research loop
- **GitHub integration** — every goal becomes an issue, every branch links to it

## Quick Start

```bash
npx create-research-flow my-project
cd my-project
claude
```

Then in Claude Code:

```
/research
```

That's it. Claude will ask for your goal, create a GitHub issue, branch, and scaffold. From there, type `/analyze` to feed in sources or `/experiment` to run code.

## The Three Layers

| Layer | Location | Role |
|---|---|---|
| **Sources** | `sources/` | Immutable raw material — write-once, never edited |
| **Working Memory** | `memory/` | LLM-maintained wiki — updated every research cycle |
| **Schema** | `CLAUDE.md` | Conventions and rules Claude reads every session |

## The Research Loop

```
/research → /analyze or /import → /experiment → /synthesize → /distill
                                                      ↓
                                          /evidence  /verify  /examples  /critique
```

Each skill is a markdown file in `.claude/skills/` — a step-by-step procedure Claude follows when you invoke it.

## Read Next

- [Getting Started](getting-started) — prerequisites and first session walkthrough
- [Claude Code Guide](claude-code-guide) — every primitive explained (hooks, skills, CLAUDE.md)
- [Git Workflow](git-workflow) — branch strategy and multi-agent dispatch
- [Memory Templates](memory-page-template) — frontmatter reference for memory pages
