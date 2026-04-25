---
name: experiment
description: Run the full experiment lifecycle — question to finding. Creates config, runs training, classifies result, writes finding, updates memory.
user_invocable: true
---

# /experiment — Run ML Experiment Lifecycle

## Gather Information

Ask the user for:
1. **Question** — Which open question are we testing? (Check `memory/open-questions/`)
2. **Hypothesis** — What specific claim will this experiment test?
3. **Acceptance criteria** — What result would confirm the hypothesis? (e.g., ">99% accuracy")
4. **Config** — New config or modify existing baseline? What to change?

## Workflow

### Step 1: Create or Select Config

1. Check `experiments/configs/baselines/` for an existing config to build on
2. Create a YAML config in `experiments/configs/` with:
   - `meta.question` linking to the open-question slug
   - `meta.hypothesis` stating the claim
   - `meta.acceptance_criteria` defining success
   - All task/architecture/training params
3. For sweeps (testing multiple variants), use the sweep format with `base:` + `runs:`

### Step 2: Run the Experiment

```bash
uv run python -m experiments.run <config.yaml>
```

Or for a dry run first:
```bash
uv run python -m experiments.run --dry-run <config.yaml>
```

### Step 3: Classify the Result

Read the run-log entry from `experiments/results/run-log.jsonl` (last line).
Read the full result JSON from `experiments/results/`.

Classify the outcome:
- **success** — met acceptance criteria → proceed to positive finding
- **partial** — completed but missed criteria → proceed to negative finding
- **inconclusive** — results ambiguous → note in finding, may re-run with more epochs
- **failed:config/bug/infra** — crashed → fix and re-run, no finding needed

### Step 4: Write Finding

Create a finding in `memory/findings/experiment-{slug}.md` following the template:

```yaml
---
title: "Experiment: [Concise result description]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: experiments/results/{result-file}.json
confidence: high
verification: source
outcome: positive | negative | inconclusive
tags: [experiment, ...]
related: [related-finding-slugs]
staleness_days: 0
---
```

**For positive results**, include:
- Insight, Evidence, Key Observations, Counter-arguments, Implications

**For negative results**, additionally include:
- Why It Failed (root cause — wrong hypothesis or wrong test?)
- What This Rules Out (what we can confidently NOT pursue)
- What This Suggests Instead (redirect for next iteration)

### Step 5: Update Memory

1. Append to `memory/log.md`:
   ```
   ## [YYYY-MM-DD] experiment | {description}
   - Config: {config-path}
   - Model: {arch} ({params} params)
   - Result: {accuracy}% — {outcome}
   - Finding: {finding-slug}
   ```

2. Update `memory/index.md` — add the finding entry

3. If the finding resolves an open question, update the question's frontmatter:
   ```yaml
   status: resolved
   resolved_by: [finding-slug]
   ```

### Step 6: Plan Next Iteration (if negative/inconclusive)

If the experiment didn't meet criteria:
1. Read the "What This Suggests Instead" section of the negative finding
2. Propose the next hypothesis and config modification
3. Optionally create the next config YAML immediately

### Step 7: Commit

```bash
git add experiments/configs/ experiments/results/ memory/
git commit -m "experiment({scope}): {brief description of result}"
```

## Conventions

- One config YAML per hypothesis (not per run — sweeps handle variants)
- Always link config → question → finding → log entry
- Negative findings are as valuable as positive ones — record them thoroughly
- Don't delete failed configs — they document what was tried
