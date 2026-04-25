# Git Workflow for Research Flow

## Branch Strategy

Research uses a hierarchical branching model designed for **parallel multi-agent exploration**.

```
main
 └── research/GH-{id}-{goal-slug}          ← research goal (parent issue)
      ├── hypothesis/GH-{id}-{angle-1}     ← agent 1 explores angle 1
      ├── hypothesis/GH-{id}-{angle-2}     ← agent 2 explores angle 2
      ├── hypothesis/GH-{id}-{angle-3}     ← agent 3 explores angle 3
      └── synthesis/GH-{id}-{consolidation} ← merge best findings
```

## Branch Types

### `research/` — Research Goal
- **Base:** `main`
- **Creates:** Parent GitHub issue (label: `research-goal`)
- **Contains:** Goal definition, initial source ingest, memory scaffolding
- **Commit prefix:** `research(scope):`
- **Merges to:** `main` when research goal is satisfied

### `hypothesis/` — Exploration Angle
- **Base:** `research/*` (the parent research branch)
- **Creates:** Sub-issue under parent (label: `hypothesis`)
- **Contains:** One specific approach/angle to the research question
- **Commit prefix:** `hypothesis(scope):`
- **Merges to:** parent `research/*` branch via PR
- **Multi-agent:** Multiple hypothesis branches can run in parallel

### `synthesis/` — Consolidation
- **Base:** `research/*` (the parent research branch)
- **Creates:** Sub-issue under parent (label: `synthesis`)
- **Contains:** Merged findings from multiple hypothesis branches
- **Commit prefix:** `synthesis(scope):`
- **Merges to:** parent `research/*` branch
- **Purpose:** Resolve contradictions, build themes, produce deliverables

### `review/` — Memory Maintenance
- **Base:** `main`
- **Creates:** Issue (label: `maintenance`)
- **Contains:** Memory lint fixes, reorganization, staleness cleanup
- **Commit prefix:** `review(scope):`
- **Merges to:** `main`

## Multi-Agent Parallel Research

When spinning up multiple agents on the same research goal:

1. Create the `research/` branch and parent issue first
2. Create N `hypothesis/` branches off the research branch
3. Each agent gets its own hypothesis branch + sub-issue
4. Agents work independently — each updates memory in their branch
5. When hypotheses complete, create a `synthesis/` branch
6. Synthesis agent reviews all hypothesis branches, cherry-picks best findings
7. Synthesis merges back to the research branch
8. Research branch merges to main when the goal is met

### Conflict Resolution in Memory

When multiple agents update the same memory files:
- `index.md` — synthesis branch rebuilds from all findings
- `log.md` — append-only, merge by concatenating chronologically
- `entities/` — check for duplicates, merge attributes
- `findings/` — each agent creates unique finding files (no conflicts)
- `themes/` — synthesis agent creates themes from all findings
- `open-questions/` — merge all, deduplicate

## GitHub Issue Hierarchy

```
Research Goal (parent issue)
 ├── Hypothesis A (sub-issue) → hypothesis/GH-{id}-a
 ├── Hypothesis B (sub-issue) → hypothesis/GH-{id}-b
 ├── Hypothesis C (sub-issue) → hypothesis/GH-{id}-c
 ├── Finding: Key insight X (sub-issue, label: finding)
 ├── Finding: Key insight Y (sub-issue, label: finding)
 └── Synthesis (sub-issue) → synthesis/GH-{id}-consolidate
```

## PR Flow

- Hypothesis → Research branch: Include findings summary in PR body
- Synthesis → Research branch: Include consolidated themes + resolved contradictions
- Research → Main: Include final report + all deliverables
