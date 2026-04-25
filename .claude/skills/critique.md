---
name: critique
description: Critical review of research results — challenge assumptions, identify weaknesses, produce honest write-up
user_invocable: true
---

# /critique — Critical Review & Write-Up

## Gather Information

Ask the user for:
1. **Scope** — Full research goal review? Specific findings/themes?
2. **Audience** — Who will read the write-up? (determines tone and depth)
3. **Harshness level** (optional) — Friendly review? Adversarial review? Peer-review simulation?
4. **Output format** — Critique report? Revised write-up? Both?

## Workflow

### Step 1: Load Full Research State

Read everything:
1. Active goal from `goals/` — especially success criteria
2. `memory/index.md`
3. All `memory/findings/`
4. All `memory/themes/`
5. All `memory/open-questions/`
6. All `outputs/` — existing deliverables, evidence, verification results, examples
7. All `sources/` — original material
8. `memory/log.md` — research history

### Step 2: Methodology Critique

Evaluate the research process itself:

1. **Source coverage** — Did we look at enough sources? Are they diverse or echo-chamber?
2. **Confirmation bias** — Did we seek disconfirming evidence as hard as confirming?
3. **Selection bias** — Did we cherry-pick findings that support a narrative?
4. **Recency bias** — Are we over-weighting recent sources?
5. **Authority bias** — Are we trusting big names without scrutiny?
6. **Scope creep/drift** — Did analysis stay within the defined scope?

### Step 3: Claims Audit

For each major finding and theme, apply adversarial review:

1. **Strength of evidence:**
   - Is the claim supported by the cited source? (re-read the source)
   - Is the reasoning chain valid? (check for logical gaps)
   - Would an expert in this field agree? What would they challenge?

2. **Alternative explanations:**
   - Could the same data support a different conclusion?
   - What confounds exist?
   - Is correlation being presented as causation?

3. **Generalizability:**
   - Does this claim hold outside the specific conditions tested?
   - What boundary conditions exist?
   - Are we over-generalizing from limited data?

4. **Reproducibility:**
   - Could someone replicate these results?
   - Are the experiments well-specified enough?
   - Were verification scripts run? Did they pass?

### Step 4: Gap Analysis

Identify what's missing:

1. **Unstated assumptions** — What are we taking for granted?
2. **Missing perspectives** — What viewpoints haven't we considered?
3. **Missing experiments** — What tests would strengthen or weaken key claims?
4. **Missing comparisons** — What baselines or alternatives weren't compared?
5. **Known unknowns** — Open questions that should have been answered by now

### Step 5: Rate Each Finding

For each finding, assign a critique rating:

| Rating | Meaning |
|--------|---------|
| **Strong** | Well-evidenced, verified, counter-arguments addressed |
| **Moderate** | Good evidence but some gaps in verification or counter-arguments |
| **Weak** | Thin evidence, unverified, or counter-arguments not addressed |
| **Challenged** | Evidence exists that contradicts this finding |
| **Unsupported** | Claim made without adequate evidence |

### Step 6: Produce Critique Report

Write `outputs/critiques/{critique-slug}.md`:

```yaml
---
title: "Critical Review: {scope}"
created: {today}
goal: {goal-slug}
reviewer: claude-critique
harshness: {friendly|standard|adversarial}
---

## Executive Assessment
{2-3 paragraphs: overall quality of the research, key strengths, key weaknesses}

## Methodology Review
| Criterion | Rating | Notes |
|-----------|--------|-------|
| Source diversity | {good/fair/poor} | {notes} |
| Confirmation bias | {low/medium/high} | {notes} |
| Selection bias | {low/medium/high} | {notes} |
| Scope adherence | {good/fair/poor} | {notes} |

## Claims Audit

### Strong Findings
{List findings rated Strong — these are the report's backbone}

### Moderate Findings
{List findings rated Moderate — what would upgrade them?}

### Weak or Challenged Findings
{List findings rated Weak/Challenged/Unsupported — these are the soft spots}

## Critical Gaps
{Numbered list of missing pieces that weaken the overall argument}

## What Would Change Our Conclusions?
{Specific experiments, data, or evidence that could overturn the main findings}

## Recommendations
1. {Specific action to strengthen the research}
2. {Specific action to address a weakness}
3. ...
```

### Step 7: Produce Revised Write-Up (if requested)

If the user wants a write-up, produce `outputs/{writeup-slug}.md` that:

1. **Leads with the strongest claims** — rated Strong or well-verified
2. **Honestly caveats weak claims** — doesn't hide uncertainty
3. **Addresses counter-arguments inline** — shows the reader we considered them
4. **Separates fact from interpretation** — clearly marks what's source-cited vs analysis
5. **Includes limitations section** — drawn from the critique
6. **References evidence and examples** — links to generated artifacts

Structure:
```yaml
---
title: "{write-up title}"
created: {today}
goal: {goal-slug}
critique: {critique-slug}
---

## Summary
{The key findings, honestly stated with confidence levels}

## Background
{Context and motivation}

## Findings
{Organized by theme, with evidence links, confidence levels, and caveats}

## Discussion
{Interpretation, implications, limitations}

## Limitations & Open Questions
{Honest accounting of what we don't know}

## Methodology
{How the research was conducted}

## References
{All sources}
```

### Step 8: Update Finding Files

For findings whose confidence changed after critique:
- Update `confidence` in frontmatter
- Add `## Critique Notes` section with the reviewer's assessment

### Step 9: Update Memory Log

Append to `memory/log.md`:
```
## [{today}] critique | {scope-description}
- Findings reviewed: {count}
- Ratings: {strong_count} strong, {moderate_count} moderate, {weak_count} weak, {challenged_count} challenged
- Critical gaps identified: {count}
- Confidence changes: {upgrades} up, {downgrades} down
- Write-up produced: {yes/no — path if yes}
- Branch: {current-branch}
```

### Step 10: Commit

```bash
git add outputs/critiques/ outputs/ memory/
git commit -m "{type}({scope}): critique — {finding_count} findings reviewed, {gap_count} gaps identified"
git push
```

## Output

Report to user:
- Executive assessment (1 paragraph)
- Findings by rating tier
- Top 3 critical gaps
- Recommendations (prioritized)
- Write-up path (if produced)
- Honest assessment: is this research ready to ship, or does it need more work?
