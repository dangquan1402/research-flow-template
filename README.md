# research-flow-template

Skeleton for an agentic research project with persistent working memory, Claude Code skills, and a GitHub Project board for tracking goals → hypotheses → findings.

**This is a template repo.** Don't clone it directly for new research — use the scaffolder:

```bash
npx create-research-flow my-project
```

The scaffolder:
- Clones this template (clean, no prior research artifacts)
- Creates a fresh GitHub repo + Project board under your account/org
- Seeds labels (`research-goal`, `hypothesis`, `finding`, `synthesis`, `maintenance`)
- Customizes board columns (`Backlog | In Progress | Synthesizing | Done`)
- Opens an optional first research-goal issue
- Runs `uv sync` + optionally launches `claude`

See [`create-research-flow`](https://github.com/dangquan1402/create-research-flow) for the CLI source.

## What's in here

```
.claude/
  skills/    Claude Code skills: /research, /analyze, /experiment,
             /synthesize, /distill, /evidence, /verify, /examples,
             /critique, /lint, /read-pdf
  hooks/     Source-immutability, branch protection, memory-update reminders
  settings.json
.github/
  ISSUE_TEMPLATE/  research-goal, hypothesis, finding
docs/
  git-workflow.md, memory-page-template.md
memory/
  index.md, log.md, entity-registry.json
  entities/, findings/, themes/, open-questions/, decisions/   (empty)
sources/                                                        (empty)
goals/                                                          (empty)
outputs/                                                        (empty)
experiments/
  run.py, train.py, framework.py, trainer.py, ...   (training harness)
  configs/baselines/   (sample experiment configs)
  configs/sweeps/      (sample sweep configs)
  results/, checkpoints/   (empty — populated by `experiments.run`)
CLAUDE.md            # The schema — read this first
pyproject.toml       # uv-managed Python deps (mlx, mlflow, pymupdf, ...)
```

## Read next

- [`CLAUDE.md`](CLAUDE.md) — the research loop, memory rules, git flow, conventions
- [`docs/git-workflow.md`](docs/git-workflow.md) — branch types and naming
- [`docs/memory-page-template.md`](docs/memory-page-template.md) — frontmatter for findings/entities/themes

## License

MIT
