---
name: distill
description: Distill findings into decisions and baseline configs — periodic synthesis that converts accumulated evidence into actionable architecture/training decisions
user_invocable: true
---

# /distill — Distill Findings into Decisions

## Gather Information

Ask the user for:
1. **Scope** — Which theme or question cluster to distill? (Check `memory/themes/`, `memory/open-questions/`)
2. **Focus** (optional) — Architecture decisions? Training decisions? Data decisions?

## Workflow

### Step 1: Gather Evidence

1. Read relevant findings from `memory/findings/experiment-*.md`
2. Read the theme(s) that synthesize these findings from `memory/themes/`
3. Read existing decision records from `memory/decisions/` to avoid duplicates
4. Check which findings are "settled" (high confidence, verified by experiment, multiple supporting results)

### Step 2: Identify Decisions

For each settled finding cluster, determine if a concrete decision can be extracted:
- Is there a clear "best config" for a specific task?
- Is there a technique that should always be used (or never used)?
- Is there an architecture parameter that has been validated?

A decision must have:
- **Clear evidence** — at least 2 experiment findings supporting it
- **No unresolved contradictions** — check for conflicting findings
- **Actionable outcome** — translates to a specific config choice

### Step 3: Write Decision Records

Create decision records in `memory/decisions/`:

```yaml
---
title: "Decision: [Concise actionable statement]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
supersedes: null
evidence:
  - finding-slug-1
  - finding-slug-2
config: baselines/config-name.yaml
tags: [architecture, training, data]
---

## Decision

[One-sentence actionable statement. E.g., "Use 2L/4H/384D for all single-operation tasks up to 5 digits."]

## Rationale

[Summary of evidence from linked findings. Why this is the right choice.]

## Tradeoffs Accepted

[What we gave up. E.g., "3.5M params is larger than looped alternative, but convergence is more reliable."]

## Revert Conditions

[When to revisit. E.g., "If parameter budget drops below 1M, switch to looped architecture."]
```

### Step 4: Create or Update Baseline Configs

For each decision, ensure a corresponding baseline config exists in `experiments/configs/baselines/`:
- Tag it with `["baseline", "verified"]`
- Reference the source result file in a comment
- Ensure `meta.question` and `meta.hypothesis` are filled in

### Step 5: Update Memory

1. Update `memory/index.md` — add Decisions section entries
2. Append to `memory/log.md`:
   ```
   ## [YYYY-MM-DD] distill | {scope}
   - Decisions created: {list}
   - Baselines updated: {list}
   - Questions resolved: {list}
   ```
3. If a decision resolves an open question, update its status

### Step 6: Commit

```bash
git add memory/decisions/ experiments/configs/baselines/ memory/index.md memory/log.md
git commit -m "synthesis({scope}): distill {N} decisions from {theme/question}"
```

## When to Run /distill

- After completing a batch of experiments on a research question
- After merging a hypothesis branch back to the research branch
- When preparing a synthesis branch
- When you notice the same config choice appearing across multiple findings

## Anti-patterns

- Don't distill from a single experiment — wait for multiple data points
- Don't create decisions for things still being actively explored
- Don't supersede a decision without running the experiment that motivates the change
