# Research Flow

An agentic research system with persistent working memory. Multiple agents can work in parallel on the same research goal from different angles, with findings compounding in a shared wiki-style memory.

## Architecture

Three layers (from Karpathy's LLM Wiki pattern):
1. **Sources** (`sources/`) — immutable raw material. Never modify after ingest.
2. **Working Memory** (`memory/`) — LLM-maintained markdown pages. Entities, findings, themes, open questions. Updated every cycle.
3. **Schema** (this file) — conventions, structure, workflows.

Plus a **validation & output layer**:
4. **Outputs** (`outputs/`) — deliverables, evidence, verification, examples, critiques.

```
outputs/
├── evidence/       # Charts, tables, plots backing claims (PNG, HTML, .py scripts)
├── verification/   # Code that checks claims programmatically (.py scripts, results.json)
├── examples/       # Worked examples illustrating findings (markdown, .py)
├── critiques/      # Critical reviews with ratings and gap analysis
└── *.md            # Final deliverables (reports, specs)
```

## Commands

- `uv sync` — install deps (loguru, pyyaml, pymupdf, tqdm; py>=3.11)
- `uv add <pkg>` — add a dependency (torch, jax, numpy, etc. — bring your own ML framework)
- `uv run ruff check .` / `uv run ruff format .` — lint/format (line-length 100, rules `E,F,I,W`)
- `uv run pre-commit run --all-files` — run all pre-commit hooks

## Automation Hooks

`.claude/hooks/` enforce repo invariants. Don't fight them — they encode rules from CLAUDE.md:

- **`block-source-modification.sh`** (PreToolUse, `Edit`) — rejects `Edit` on anything under `sources/`. Sources are immutable; create a new `memory/findings/` page instead.
- **`block-commit-protected-branch.sh`** (PreToolUse, `Bash`) — blocks `git commit` while on `main`. Create a `research/`, `hypothesis/`, `synthesis/`, or `review/` branch first.
- **`post-memory-update.sh`** (PostToolUse, `Edit|Write`) — after editing anything in `memory/` (other than `index.md`/`log.md`/`entity-registry.json`), prints a reminder to update `memory/index.md` and append to `memory/log.md`. Do it in the same turn.

## Git Flow for Research

| Branch Type | Base | Prefix | Purpose |
|---|---|---|---|
| `research/` | `main` | `research(scope):` | New research goal — creates parent GH issue |
| `hypothesis/` | `research/*` | `hypothesis(scope):` | One angle/approach on a research goal — sub-issue |
| `synthesis/` | `research/*` | `synthesis(scope):` | Merge findings from multiple hypothesis branches |
| `review/` | `main` | `review(scope):` | Lint, reorganize, resolve contradictions in memory |

**Multi-agent parallel work:** Spin up agents on separate `hypothesis/` branches off the same `research/` branch. Each agent explores a different angle. `synthesis/` branches merge the best findings.

**Branch naming:** `{type}/GH-{issue}-{slug}`
Example: `hypothesis/GH-7-attention-mechanisms`, `synthesis/GH-5-consolidate-transformer-findings`

## GitHub Project Tracking

- **Project:** _(set by `create-research-flow` at scaffold time — see your GitHub repo's Projects tab)_
- **Repo:** _(this repo)_
- Each research goal = parent issue (label: `research-goal`)
- Each hypothesis/approach = sub-issue under the parent (label: `hypothesis`)
- Each significant finding = sub-issue (label: `finding`)
- Synthesis tasks get label: `synthesis`
- Memory maintenance gets label: `maintenance`
- Project board columns: `Backlog | In Progress | Synthesizing | Done`
- Link all branches to their issues
- Use `gh project item-add <number> --owner <owner> --url {issue_url}` to add issues to the project board
- Issue templates live in `.github/ISSUE_TEMPLATE/`: `research-goal.md`, `hypothesis.md`, `finding.md` — use them when opening issues so labels/structure are correct

### Multi-Agent Dispatch

To spin up parallel hypothesis agents:
```
Agent({
  isolation: "worktree",
  prompt: "Research goal: {goal}. Your hypothesis angle: {angle}. Branch: hypothesis/GH-{id}-{slug}. Work in memory/ following CLAUDE.md conventions. When done, commit and push.",
  description: "Hypothesis: {angle}"
})
```
Each agent gets its own worktree (isolated branch). No conflicts during parallel work.

## Memory Structure

```
memory/
├── index.md             # Catalog of all pages with summaries (updated every ingest)
├── log.md               # Append-only chronological record of all operations
├── entity-registry.json # Dedup index — check before creating an entity page
├── entities/            # People, orgs, concepts, tools discovered
├── findings/            # Discrete insights (positive, negative, inconclusive) with citations
├── themes/              # Cross-cutting patterns across findings
├── open-questions/      # Gaps identified, queued for experiments
└── decisions/           # Distilled actionable decisions (from `/distill`)
```

### Memory Rules
- Every memory page has YAML frontmatter: `title`, `created`, `updated`, `source`, `confidence` (high/medium/low), `tags`
- `index.md` is updated after every ingest/analyze/synthesize operation
- `log.md` is append-only with format: `## [YYYY-MM-DD] operation | subject`
- Findings reference their source with `[source-slug]` citations
- Themes cross-reference findings they synthesize
- Open questions link to the research goal they serve

### Memory Hygiene
- No orphan pages (everything in index.md)
- No duplicate entities (check before creating)
- Stale findings (>30 days without re-validation) get flagged
- Contradictions between findings must be surfaced in open-questions/

## Research Loop

1. **Init** (`/research`) — Define goal → create issue → create branch → scaffold
2. **Ingest** (`/analyze`) — Feed source → extract entities/findings → update memory → log
3. **Analyze** (`/analyze`) — Read goal + memory → identify gaps → generate new analysis → update memory
4. **Experiment** (`/experiment`) — Design hypothesis → create config → run → classify → write finding (see below)
5. **Synthesize** (`/synthesize`) — Consolidate findings → build themes → resolve contradictions → produce output
6. **Distill** (`/distill`) — Extract decisions from settled findings → baseline configs → decision records
7. **Evidence** (`/evidence`) — Generate charts, tables, plots backing key claims → `outputs/evidence/`
8. **Verify** (`/verify`) — Generate code that checks intermediate & final claims → `outputs/verification/`
9. **Examples** (`/examples`) — Generate worked examples illustrating findings → `outputs/examples/`
10. **Critique** (`/critique`) — Adversarial review of results, gap analysis, honest write-up → `outputs/critiques/`
11. **Lint** (`/lint`) — Health-check memory: orphans, contradictions, staleness, missing cross-refs

**Ingest helpers:**
- **`/read-pdf`** — Render a PDF (paper, report, scan) to one PNG per page via PyMuPDF, then read the images directly. Preserves figures, tables, equations, and scanned text that text extraction would lose. Output goes to `sources/_pdf-images/<slug>/`.

**Infrastructure helpers:**
- **`/vastai`** — Rent and manage GPU instances on Vast.ai. Subcommands: `rent`, `status`, `ssh`, `jupyter`, `sync`, `terminate`. State tracked in `experiments/.vastai-instance.json` (gitignored). Use when an experiment needs GPU compute the local machine can't provide.

Steps 7-10 form the **validation & presentation layer** — they can be run in any order after synthesis, and each strengthens the others (e.g., verification failures inform critique, examples clarify evidence).

## Experiment Workflow

The experiment lifecycle connects open questions to actionable decisions. The `experiments/` folder is a blank scaffold — add your own training code, scripts, or notebooks using whatever framework fits your project (`uv add torch`, `uv add jax`, etc.).

```
QUESTION (memory/open-questions/)
    |
    v
HYPOTHESIS → write your experiment script → experiments/
    |
    v
RESULT → log to experiments/results/run-log.jsonl
    |
    |-- success -------> FINDING --> may close QUESTION
    |-- partial -------> NEGATIVE FINDING --> refine HYPOTHESIS --> re-run
    |-- inconclusive --> adjust and re-run
    |
    v (periodically)
DISTILL --> DECISION RECORD (memory/decisions/)
```

### Logging Convention

Append each run to `experiments/results/run-log.jsonl` — one JSON object per line:

```json
{"date": "YYYY-MM-DD", "experiment": "slug", "status": "success|partial|inconclusive|failed", "notes": "..."}
```

### Failure Classification

| Status | Meaning | Action |
|--------|---------|--------|
| `success` | Met acceptance criteria | Write positive finding |
| `partial` | Completed, missed criteria | Write negative finding, iterate |
| `inconclusive` | Ambiguous results | Record, may re-run |
| `failed` | Bug, config, or infra issue | Fix and re-run |

### Decision Records

Distilled from settled findings into `memory/decisions/`. Each decision:
- Links to evidence (finding slugs)
- Has revert conditions (when to revisit)
- Status: `active` | `superseded` | `reverted`

## Quality Patterns

### Verification Gates
Every finding is classified:
- `source` — directly cited from primary material
- `analysis` — inference with reasoning chain shown
- `unverified` — noted but not validated
- `gap` — explicitly missing information

### FUNGI Counter-Arguments
Every finding and theme MUST answer: "What would disprove this?"
This resists confirmation bias and forces rigorous thinking.

### Staleness Scoring
Pages track `staleness_days` in frontmatter. `/lint` increments this. Pages >30 days stale get flagged.

### Entity Registry
`memory/entity-registry.json` prevents duplicate entity pages. Always check before creating.

## Conventions

- Commit messages: `{type}({scope}): description` (e.g., `research(transformers): ingest attention paper`)
- One finding per file in `findings/`
- One entity per file in `entities/`
- Themes can reference multiple findings
- Sources are immutable after creation (enforced by hook)
- Always run `pre-commit` and `ruff` after coding changes
- Memory page frontmatter templates in `docs/memory-page-template.md`
- `experiments/` is a blank scaffold — add your own scripts and framework
- Dependencies managed with `uv` — install: `uv sync`, add: `uv add <pkg>`, run: `uv run <cmd>`
