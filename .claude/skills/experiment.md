---
name: experiment
description: Run the full experiment lifecycle — question to finding. Designs hypothesis, runs your experiment code, classifies result, writes finding, updates memory.
user_invocable: true
---

# /experiment — Experiment Lifecycle

This skill is framework-agnostic. You bring the training code (`experiments/`); this skill handles the research loop around it — connecting questions to hypotheses, classifying results, and writing findings into memory.

## Gather Information

Ask the user for:
1. **Question** — Which open question are we testing? (Check `memory/open-questions/`)
2. **Hypothesis** — What specific claim will this experiment test?
3. **Acceptance criteria** — What result would confirm the hypothesis? (e.g., ">90% accuracy", "loss < 0.1")
4. **How to run** — What command or script runs this experiment?

## Workflow

### Step 1: Write an Experiment Plan

Create `experiments/configs/<slug>.md` (or a YAML config if your framework uses them) documenting:

```markdown
# Experiment: <slug>

- **Question**: links to `memory/open-questions/<slug>.md`
- **Hypothesis**: the specific claim being tested
- **Acceptance criteria**: what success looks like
- **Setup**: what to run, key hyperparameters
```

### Step 2: Run the Experiment

Run the user's experiment script — whatever is in `experiments/`. Ask the user to run it if it requires a GPU or long-running process. Wait for results before proceeding.

Log the outcome to `experiments/results/run-log.jsonl` (append one line):

```json
{"date": "YYYY-MM-DD", "experiment": "<slug>", "status": "success|partial|inconclusive|failed", "metric": "<key result>", "notes": "<brief observation>"}
```

### Step 3: Classify the Result

| Status | Meaning | Next step |
|--------|---------|-----------|
| `success` | Met acceptance criteria | Write positive finding |
| `partial` | Completed but missed criteria | Write negative finding, propose iteration |
| `inconclusive` | Ambiguous — not enough signal | Note and consider re-running |
| `failed` | Crashed (bug, OOM, config error) | Fix and re-run — no finding needed |

### Step 4: Write Finding

Create `memory/findings/experiment-<slug>.md`:

```yaml
---
title: "Experiment: [Concise result description]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: experiments/results/run-log.jsonl
confidence: high
verification: source
outcome: positive | negative | inconclusive
tags: [experiment]
related: []
staleness_days: 0
---
```

**For positive results**, include:
- **Insight** — what we learned
- **Evidence** — the actual numbers
- **Counter-arguments** — what would disprove this?
- **Implications** — what this means for the research goal

**For negative results**, additionally include:
- **Why It Failed** — wrong hypothesis, or wrong test?
- **What This Rules Out** — what we can confidently stop pursuing
- **What This Suggests Instead** — redirect for next iteration

### Step 5: Update Memory

1. Append to `memory/log.md`:
   ```
   ## [YYYY-MM-DD] experiment | <description>
   - Hypothesis: <claim>
   - Result: <key metric> — <outcome>
   - Finding: <finding-slug>
   ```

2. Add finding to `memory/index.md`

3. If this resolves an open question, update its frontmatter:
   ```yaml
   status: resolved
   resolved_by: [finding-slug]
   ```

### Step 6: Plan Next Iteration (if negative/inconclusive)

1. Read "What This Suggests Instead" from the negative finding
2. Propose the next hypothesis
3. Optionally scaffold the next experiment plan immediately

### Step 7: Commit

```bash
git add experiments/ memory/
git commit -m "experiment({scope}): {brief description of result}"
```

## Conventions

- One experiment plan per hypothesis — document before running
- Always link: question → experiment → finding → log entry
- Negative findings are as valuable as positive ones — record them thoroughly
- Don't delete failed configs — they document what was tried
