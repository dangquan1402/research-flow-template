---
name: verify
description: Generate and save code that programmatically verifies key intermediate and final claims from findings
user_invocable: true
---

# /verify — Generate Verification Code

## Gather Information

Ask the user for:
1. **Scope** — All findings? Specific claims? A theme?
2. **Verification depth** — Quick sanity checks? Full reproduction? Statistical tests?
3. **Data availability** — Are experiment results available? Need to run new experiments?

## Workflow

### Step 1: Load Context

Read in order:
1. Active goal from `goals/`
2. `memory/index.md`
3. All files in `memory/findings/`
4. All files in `memory/themes/`
5. `experiments/results/` — existing experiment data
6. `experiments/config.py` — available experiment parameters
7. `outputs/evidence/` — any existing evidence artifacts

### Step 2: Decompose Claims Into Verifiable Assertions

For each finding/theme in scope:

1. **Extract the claim chain** — break down the argument into:
   - **Premises** (assumed or cited facts)
   - **Intermediate claims** (derived from premises via reasoning)
   - **Final claims** (the stated finding/conclusion)

2. **Classify each claim by verifiability:**
   - `empirical` — can be checked by running an experiment or querying data
   - `analytical` — can be checked by logical/mathematical derivation
   - `comparative` — can be checked by comparing against baselines or alternatives
   - `statistical` — needs statistical significance testing
   - `not-verifiable` — subjective or requires external data we don't have

3. **Prioritize:** Focus on claims where verification would most change confidence levels.

### Step 3: Generate Verification Scripts

For each verifiable claim, create `outputs/verification/{claim-slug}_verify.py`:

```python
"""
Verification: {claim being verified}
Finding: {finding-slug}
Verification type: {empirical|analytical|comparative|statistical}
Generated: {today}

Expected outcome: {what we expect if claim holds}
Falsification: {what we expect if claim is wrong}
"""

def verify_{claim_slug}():
    """
    Claim: {the claim in plain English}
    Method: {how we verify it}
    """
    # ... verification logic ...
    
    # RESULT
    result = {
        "claim": "{claim text}",
        "verified": True/False,
        "expected": "{expected value/behavior}",
        "actual": "{actual value/behavior}",
        "confidence_delta": "{how this changes our confidence}",
        "notes": "{any caveats or limitations}"
    }
    return result

if __name__ == "__main__":
    import json
    result = verify_{claim_slug}()
    print(json.dumps(result, indent=2))
    if result["verified"]:
        print("PASS: Claim verified")
    else:
        print("FAIL: Claim NOT verified — review finding")
```

**Types of verification code:**

- **Empirical:** Run a focused experiment (using `experiments/` framework) and check results match the claim
- **Analytical:** Compute expected values, check bounds, verify mathematical relationships
- **Comparative:** Run baseline vs claimed approach, compare metrics
- **Statistical:** Compute p-values, confidence intervals, effect sizes

### Step 4: Run Verification Suite

Execute all verification scripts:
```bash
for f in outputs/verification/*_verify.py; do
    echo "=== Running: $f ==="
    python "$f"
    echo ""
done
```

Collect results into `outputs/verification/results.json`:
```json
{
  "run_date": "{today}",
  "goal": "{goal-slug}",
  "results": [
    {
      "claim_slug": "...",
      "finding": "...",
      "verified": true,
      "details": "..."
    }
  ],
  "summary": {
    "total": N,
    "passed": N,
    "failed": N,
    "skipped": N
  }
}
```

### Step 5: Create Verification Report

Write `outputs/verification/report.md`:
```yaml
---
title: "Verification Report"
created: {today}
goal: {goal-slug}
---

## Summary

| Status | Count | % |
|--------|-------|---|
| Verified | {n} | {%} |
| Failed | {n} | {%} |
| Skipped | {n} | {%} |
| Not verifiable | {n} | {%} |

## Results by Finding

### {finding-title}

| Claim | Type | Status | Notes |
|-------|------|--------|-------|
| {claim} | {type} | PASS/FAIL | {notes} |

## Failed Verifications

{For each failed claim: what went wrong, what this means for the finding's confidence, recommended action}

## Verification Gaps

{Claims we couldn't verify and why — data missing, computation too expensive, etc.}
```

### Step 6: Update Finding Confidence Levels

For findings where verification changed our confidence:
- If all claims verified: consider upgrading confidence to `high`
- If key claims failed: downgrade confidence, add note about what failed
- Update the finding file's `verification` field and add a `## Verification` section:
```markdown
## Verification
- Verified: {date}
- Script: `outputs/verification/{claim-slug}_verify.py`
- Result: PASS/FAIL
- Notes: {any caveats}
```

### Step 7: Update Memory Log

Append to `memory/log.md`:
```
## [{today}] verify | {scope-description}
- Claims verified: {pass_count}/{total_count}
- Failed verifications: {fail_count} ({list})
- Confidence upgrades: {count}
- Confidence downgrades: {count}
- Branch: {current-branch}
```

### Step 8: Commit

```bash
git add outputs/verification/ memory/
git commit -m "{type}({scope}): verify claims — {pass_count}/{total_count} passed"
git push
```

## Output

Report to user:
- Verification summary (pass/fail/skip counts)
- Any **failed verifications** (high priority — these challenge existing findings)
- Confidence level changes
- Claims that couldn't be verified and why
- Recommended next steps (re-run experiments, revise findings, investigate failures)
