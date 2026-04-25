---
name: synthesize
description: Consolidate findings into themes, resolve contradictions, merge hypothesis branches, produce deliverables
user_invocable: true
---

# /synthesize — Consolidate & Produce

## Gather Information

Ask the user for:
1. **Scope** — Synthesize everything? Or specific findings/themes?
2. **Output format** (optional) — Report, summary, comparison table, recommendations?
3. **Merge branches?** — Should we merge hypothesis branches into the research branch?

## Workflow

### Step 1: Load Full Memory State

Read in order:
1. Active goal from `goals/`
2. `memory/index.md` — full catalog
3. All files in `memory/findings/` — every discrete insight
4. All files in `memory/themes/` — existing themes
5. All files in `memory/open-questions/` — known gaps
6. `memory/entity-registry.json` — known entities

### Step 2: If Merging Hypothesis Branches

For each hypothesis branch to merge:

1. List what the hypothesis branch added:
```bash
git log research/{parent}..hypothesis/{branch} --oneline
git diff research/{parent}...hypothesis/{branch} -- memory/
```

2. Create synthesis branch:
```bash
git checkout research/GH-{parent}-{slug}
git checkout -b synthesis/GH-{issue}-consolidate-{slug}
```

3. Cherry-pick or merge findings from each hypothesis branch
4. Resolve conflicts in memory files:
   - `index.md` — rebuild from all findings
   - `log.md` — concatenate chronologically
   - `entities/` — deduplicate via entity registry
   - `findings/` — each agent creates unique files (should be conflict-free)

### Step 3: Identify Themes

Look across all findings for cross-cutting patterns:

For each theme, create `memory/themes/{theme-slug}.md` using the theme template.

**Critical — apply FUNGI counter-argument:**
- Each theme MUST include contradictions and counter-arguments
- What findings tension with this theme?
- What would disprove it?

### Step 4: Resolve Contradictions

For findings that contradict each other:
1. Document the contradiction in both finding files
2. Create an open question if resolution needs more research
3. If resolvable: update confidence levels, add reasoning
4. If irresolvable: note it in the theme as an open tension

### Step 5: Produce Output

Write `outputs/{deliverable-slug}.md`:
```yaml
---
title: "{deliverable title}"
created: {today}
goal: {goal-slug}
type: report | summary | comparison | recommendations
---

## Executive Summary
{2-3 paragraphs — the key takeaway}

## Key Findings
{numbered list of top findings with confidence levels}

## Themes
{cross-cutting patterns discovered}

## Open Questions
{what we still don't know}

## Methodology
{how this research was conducted — branches, sources, agents}

## Sources
{full citation list}
```

### Step 6: Update Memory

- Update `memory/index.md` with new themes
- Append to `memory/log.md`:
```
## [{today}] synthesize | {deliverable-title}
- Themes created: {count} ({list})
- Contradictions resolved: {count}
- Contradictions open: {count}
- Output: outputs/{deliverable-slug}.md
- Branches merged: {list}
```

### Step 7: Update GitHub Issues

```bash
# Comment on parent research issue
gh issue comment {parent_issue} --body "## Synthesis Complete ({today})
- Output: outputs/{deliverable-slug}.md
- Themes: {count}
- Open questions remaining: {count}
- Status: {assessment of goal completion}"

# Close hypothesis sub-issues that were merged
gh issue close {sub_issue_number} --comment "Merged into synthesis. Key findings: {summary}"

# Update project board status if goal is met
```

### Step 8: Assess Goal Completion

Compare output against success criteria in the goal file.
- If met: recommend closing the research goal
- If not: identify what's still needed, recommend next `/analyze` cycle

### Step 9: Commit and PR

```bash
git add memory/ outputs/
git commit -m "synthesis({scope}): consolidate findings — {theme_count} themes, {finding_count} findings"
git push -u origin {branch_name}
```

If merging to research branch:
```bash
gh pr create \
  --title "Synthesis: {title}" \
  --base research/GH-{parent}-{slug} \
  --body "## Synthesis Summary\n{summary}\n\n## Themes\n{themes}\n\n## Merged Hypotheses\n{list}"
```

## Output

Report to user:
- Themes discovered
- Contradictions found (resolved and open)
- Deliverable path
- Goal completion assessment
- Recommended next steps
