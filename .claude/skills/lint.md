---
name: lint
description: Health-check working memory — find orphans, contradictions, staleness, missing cross-refs, duplicate entities
user_invocable: true
---

# /lint — Memory Health Check

## Workflow

### Step 1: Load Memory State

Read:
1. `memory/index.md`
2. All files in `memory/entities/`, `memory/findings/`, `memory/themes/`, `memory/open-questions/`
3. `memory/entity-registry.json`

### Step 2: Check for Orphan Pages

- Scan all .md files in memory subdirectories
- Check each file is listed in `memory/index.md`
- **Fix:** Add missing entries to index

### Step 3: Check for Duplicate Entities

- Compare entity filenames and aliases in `entity-registry.json`
- Look for entities with similar names (fuzzy match)
- **Fix:** Merge duplicates, update registry, update all references

### Step 4: Check for Stale Pages

- Read `updated` frontmatter field on every page
- Calculate days since last update
- Update `staleness_days` field
- Flag pages with `staleness_days > 30`
- **Report:** List stale pages sorted by staleness

### Step 5: Check Cross-References

- For each finding: verify `source` field points to an existing source file
- For each theme: verify `synthesizes` list points to existing finding files
- For each entity: verify `related` entries exist
- **Fix:** Remove broken references, flag missing sources

### Step 6: Check for Contradictions

- Read all findings
- Look for findings that make opposing claims about the same entity or topic
- Check if contradictions are already documented in themes or open-questions
- **Report:** List undocumented contradictions

### Step 7: Check Verification Coverage

Tally verification gate distribution:
- `source` — cited claims (target: >40%)
- `analysis` — reasoned claims (target: <40%)
- `unverified` — unflagged claims (target: <15%)
- `gap` — known unknowns (info only)

**Report:** Verification coverage percentages and any findings that should be upgraded.

### Step 8: Check Counter-Arguments (FUNGI)

- Every finding and theme MUST have a non-empty "Counter-arguments" section
- Flag any pages missing counter-arguments
- **Fix:** Add placeholder counter-argument sections

### Step 9: Check Open Questions Relevance

- For each open question: does it still relate to an active goal?
- Are any open questions now answered by existing findings?
- **Fix:** Close answered questions, flag orphaned questions

### Step 10: Generate Lint Report

Append to `memory/log.md`:
```
## [{today}] lint | Memory health check
- Orphan pages found/fixed: {count}
- Duplicate entities found/merged: {count}
- Stale pages (>30 days): {count}
- Broken cross-refs found/fixed: {count}
- Undocumented contradictions: {count}
- Missing counter-arguments: {count}
- Verification coverage: source {n}% | analysis {n}% | unverified {n}% | gap {n}%
- Answered open questions closed: {count}
```

### Step 11: Commit Fixes

```bash
git add memory/
git commit -m "review(memory): lint — {fixes_count} fixes, {issues_count} issues flagged"
```

## Output

Report to user:
- Summary table of all checks (pass/fail/fixed)
- List of issues that need human judgment
- Recommended next actions
- Overall memory health score (% of checks passing)
