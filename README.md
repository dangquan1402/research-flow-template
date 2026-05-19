# research-flow-template

Skeleton for an agentic research project with persistent working memory, Claude Code skills, and a GitHub Project board for tracking goals → hypotheses → findings.

**This is a template repo.** Use the scaffolder to start a new project:

```bash
npx create-research-flow my-project
```

The scaffolder clones this template, creates a GitHub repo + Project board, seeds labels and board columns, runs `uv sync`, and opens Claude Code.

## What's included

```
.claude/
  skills/     /research, /analyze, /import, /experiment, /synthesize,
              /distill, /evidence, /verify, /examples, /critique,
              /lint, /read-pdf
  hooks/      Source immutability, branch protection, memory-update reminders
  settings.json

.github/
  ISSUE_TEMPLATE/   research-goal, hypothesis, finding

docs/
  claude-code-guide.md    Every Claude Code primitive explained
  git-workflow.md         Branch strategy and multi-agent dispatch
  memory-page-template.md Frontmatter templates for memory pages

memory/
  index.md, log.md, entity-registry.json
  entities/, findings/, themes/, open-questions/, decisions/

sources/                  Immutable raw material (write-once)
goals/                    Active research goal definitions
outputs/                  Deliverables (reports, evidence, verification, examples, critiques)
experiments/              Blank scaffold — add your own training code and framework

CLAUDE.md                 The research loop, memory rules, git flow, conventions
pyproject.toml            uv-managed Python deps (loguru, pyyaml, pymupdf, tqdm)
```

## How it works

Claude Code reads `CLAUDE.md` on every session start. Hooks enforce invariants automatically. Skills give Claude step-by-step procedures for each phase of the research loop.

The three-layer memory model:
1. **Sources** (`sources/`) — immutable raw material, never edited after creation
2. **Working Memory** (`memory/`) — LLM-maintained wiki updated every research cycle
3. **Schema** (`CLAUDE.md`) — conventions and rules Claude always has in context

## Read next

- [`CLAUDE.md`](CLAUDE.md) — start here
- [`docs/getting-started.md`](docs/getting-started.md) — prerequisites and first session
- [`docs/sample-pipeline.md`](docs/sample-pipeline.md) — **15-min end-to-end canary on Vast.ai** (rent → train → report) with verify checkpoints at every step
- [`docs/claude-code-guide.md`](docs/claude-code-guide.md) — full explanation of every Claude Code primitive
- [`docs/git-workflow.md`](docs/git-workflow.md) — branch types and naming
- [`docs/memory-page-template.md`](docs/memory-page-template.md) — frontmatter for memory pages

## Browse docs locally

```bash
gem install bundler && bundle install
bundle exec jekyll serve
# open http://localhost:4000
```

## License

MIT
