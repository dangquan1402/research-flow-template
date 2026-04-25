---
name: evidence
description: Generate and save graphical evidence (charts, tables, plots) backing key claims from findings
user_invocable: true
---

# /evidence — Generate Graphical Evidence

## Gather Information

Ask the user for:
1. **Scope** — All findings? Specific findings or themes? A particular claim?
2. **Format preferences** (optional) — Chart types, table styles, HTML vs PNG vs both?
3. **Data source** — Use existing experiment results? Memory findings? Both?

## Workflow

### Step 1: Load Context

Read in order:
1. Active goal from `goals/`
2. `memory/index.md` — full catalog
3. All files in `memory/findings/` — every discrete insight
4. All files in `memory/themes/` — cross-cutting patterns
5. `experiments/results/` — any experimental data available

### Step 2: Identify Claims That Need Visual Evidence

For each finding/theme in scope:
1. Extract the **key quantitative claims** (numbers, comparisons, trends)
2. Extract the **key qualitative claims** that benefit from visual representation (taxonomies, relationships, hierarchies)
3. Prioritize claims by:
   - **confidence level** — high-confidence claims need evidence to convince; low-confidence claims need evidence to evaluate
   - **centrality to the research goal** — core claims > peripheral ones
   - **counter-argument strength** — stronger counter-arguments need stronger evidence

### Step 3: Generate Evidence Artifacts

For each claim that needs visual backing, create one or more of:

**Tables** (Markdown or HTML):
- Comparison tables showing data side-by-side
- Summary tables of experimental results
- Decision matrices with criteria and scores

**Charts** (Python script + saved output):
- Bar charts for comparisons
- Line charts for trends/convergence
- Heatmaps for multi-dimensional comparisons
- Scatter plots for correlations

Generate a Python script at `outputs/evidence/{evidence-slug}.py`:
```python
"""
Evidence: {claim being supported}
Finding: {finding-slug}
Generated: {today}
"""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# ... chart/table generation code ...

plt.savefig('outputs/evidence/{evidence-slug}.png', dpi=150, bbox_inches='tight')
print(f"Saved: outputs/evidence/{evidence-slug}.png")
```

Run the script to generate the output:
```bash
python outputs/evidence/{evidence-slug}.py
```

**HTML Tables** (for rich formatting):
Write directly to `outputs/evidence/{evidence-slug}.html` for complex tables that need styling.

### Step 4: Create Evidence Index

Write or update `outputs/evidence/index.md`:
```yaml
---
title: "Evidence Index"
created: {today}
updated: {today}
goal: {goal-slug}
---

## Evidence Artifacts

| # | Claim | Finding | Type | File | Status |
|---|-------|---------|------|------|--------|
| 1 | {claim summary} | {finding-slug} | chart/table | {filename} | generated |
| 2 | ... | ... | ... | ... | ... |
```

### Step 5: Link Evidence Back to Findings

For each finding that now has evidence:
- Update the finding file to add an `## Evidence` section:
```markdown
## Evidence
- [{evidence-title}](../../outputs/evidence/{filename}) — {description}
```

### Step 6: Update Memory Log

Append to `memory/log.md`:
```
## [{today}] evidence | {scope-description}
- Evidence artifacts generated: {count}
- Charts: {count} | Tables: {count} | HTML: {count}
- Findings backed: {list}
- Branch: {current-branch}
```

### Step 7: Commit

```bash
git add outputs/evidence/ memory/
git commit -m "{type}({scope}): generate evidence — {count} artifacts for {finding_count} findings"
git push
```

## Output

Report to user:
- List of evidence artifacts generated (with file paths)
- Which findings now have visual backing
- Which key claims still lack evidence
- Any data gaps that prevent generating evidence (recommend `/analyze` or experiments)
