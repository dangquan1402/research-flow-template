---
name: analyze
description: Ingest sources and run analysis — extracts entities/findings, updates working memory, identifies gaps
user_invocable: true
---

# /analyze — Ingest & Analyze

## Gather Information

Ask the user for:
1. **Source** — URL, file path, paste, or topic to research
2. **Focus** (optional) — Specific aspect to focus on? Or broad sweep?

## Workflow

### Step 1: Identify Active Research Context

Read the current branch name to determine the active research goal:
- If on `research/` or `hypothesis/` branch → use that context
- If on `main` → ask which goal to work on, or check `goals/` for active goals

Read the goal file from `goals/` to understand the research question and scope.

### Step 2: Ingest the Source

If URL: fetch and extract content.
If file: read the file.
If topic: use web search to gather information.

Create source file `sources/{source-slug}.md`:
```yaml
---
title: "{source title}"
created: {today}
type: url | paper | document | web-search
url: "{url if applicable}"
ingested_by: "{branch-name}"
---

## Summary
{2-3 paragraph summary}

## Key Points
- {point 1}
- {point 2}
...
```

Sources are **immutable** after creation. Never modify a source file.

### Step 3: Extract Entities

For each significant entity (person, org, concept, tool, paper):

1. **Check entity registry** — read `memory/entity-registry.json`
2. If entity exists: update the existing entity file with new information
3. If new: create entity file and register in `entity-registry.json`

Entity file: `memory/entities/{entity-slug}.md` (use template from `docs/memory-page-template.md`)

### Step 4: Extract Findings

For each discrete insight:

Create `memory/findings/{finding-slug}.md` using the finding template.

**Critical — apply verification gates:**
- `source` — directly cited? Include the citation.
- `analysis` — show the reasoning chain.
- `unverified` — flag it clearly.
- `gap` — what's missing that we need?

**Critical — apply FUNGI counter-argument:**
- Every finding MUST include a "Counter-arguments" section
- Ask: "What would disprove this?"

### Step 5: Identify Open Questions

For each gap or follow-up discovered:

Create `memory/open-questions/{question-slug}.md`:
```yaml
---
title: "Question: {question}"
created: {today}
updated: {today}
source: {source-slug or finding-slug}
priority: high | medium | low
tags: []
related: []
---

## Question
{full question}

## Why This Matters
{connection to research goal}

## Possible Approaches
- {approach 1}
- {approach 2}
```

### Step 6: Update Memory Index

Read `memory/index.md` and update all sections with new/modified pages.
Each entry: `- [Title](path) — one-line summary | confidence | updated`

### Step 7: Update Memory Log

Append to `memory/log.md`:
```
## [{today}] ingest | {source-title}
- Source: sources/{source-slug}.md
- Entities created/updated: {count} ({list})
- Findings created: {count} ({list})
- Open questions created: {count} ({list})
- Branch: {current-branch}
```

### Step 8: Read Goal + Memory for Gap Analysis

After ingesting, read:
- The active goal file
- `memory/index.md` (full picture of what we know)
- `memory/open-questions/` (what we don't know)

Produce a brief **gap analysis**:
- What do we know now?
- What's still missing relative to the success criteria?
- What should we investigate next?

### Step 9: Update GitHub Issue

Update the relevant issue with a progress comment:
```bash
gh issue comment {issue_number} --body "## Analysis Update ({today})
- Ingested: {source-title}
- New findings: {count}
- Key insight: {top finding}
- Next: {recommended next step}"
```

### Step 10: Commit

```bash
git add sources/ memory/ goals/
git commit -m "{type}({scope}): ingest {source-slug} — {count} findings, {count} entities"
git push
```

## Output

Report to user:
- Findings extracted (with confidence levels)
- Entities discovered
- Open questions identified
- Gap analysis relative to research goal
- Recommended next step
