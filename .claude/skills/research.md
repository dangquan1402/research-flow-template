---
name: research
description: Start a new research goal — creates parent GH issue, project tracking, research branch, and scaffolds memory
user_invocable: true
---

# /research — Start a New Research Goal

## Gather Information

Ask the user for:
1. **Research question/goal** — What are we trying to learn or prove?
2. **Scope** — What's in/out of bounds?
3. **Success criteria** — How do we know when we're done?
4. **Initial sources** (optional) — Any URLs, papers, docs to start with?
5. **Parallel angles** (optional) — Should we spin up multiple hypothesis branches? How many?

## Workflow

### Step 1: Create GitHub Issue (Parent)

```bash
gh issue create \
  --title "Research: {goal-title}" \
  --label "research-goal" \
  --body "$(cat <<'EOF'
## Research Goal
{user's research question}

## Scope
{scope}

## Success Criteria
{criteria}

## Initial Sources
{sources list}

## Status
- [ ] Goal defined
- [ ] Initial sources ingested
- [ ] Hypothesis branches created
- [ ] Findings synthesized
- [ ] Output delivered
EOF
)"
```

### Step 2: Add Issue to GitHub Project

```bash
gh project item-add {PROJECT_NUMBER} --owner dangquan1402 --url {issue_url}
```

### Step 3: Create Research Branch

```bash
git checkout main
git checkout -b research/GH-{issue_number}-{goal-slug}
```

### Step 4: Create Goal File

Write `goals/{goal-slug}.md`:
```yaml
---
title: "{goal title}"
created: {today}
issue: GH-{issue_number}
status: active
scope: "{scope}"
success_criteria: "{criteria}"
---

## Research Question
{full question}

## Approach
{planned approach}

## Sources
- {source list}
```

### Step 5: Log the Operation

Append to `memory/log.md`:
```
## [{today}] create | Research goal: {title}
- Issue: GH-{issue_number}
- Branch: research/GH-{issue_number}-{goal-slug}
- Scope: {scope}
```

### Step 6: If Parallel Angles Requested

For each hypothesis angle:

1. Create sub-issue:
```bash
gh issue create \
  --title "Hypothesis: {angle-title}" \
  --label "hypothesis" \
  --body "Parent: #{parent_issue_number}\n\n## Angle\n{description}"
```

2. Link as sub-issue:
```bash
gh api repos/{owner}/{repo}/issues/{parent_issue}/sub_issues --method POST -f sub_issue_id={sub_issue_id}
```

3. Create hypothesis branch:
```bash
git checkout research/GH-{parent}-{goal-slug}
git checkout -b hypothesis/GH-{sub_issue}-{angle-slug}
```

4. Each hypothesis branch can be assigned to a parallel agent via:
```
Agent({ isolation: "worktree", prompt: "..." })
```

### Step 7: Commit and Push

```bash
git add goals/ memory/
git commit -m "research({goal-slug}): init research goal GH-{issue_number}"
git push -u origin {branch_name}
```

## Output

Report to user:
- Parent issue URL
- Branch name
- Goal file path
- Sub-issues created (if any)
- Next step: run `/analyze` to ingest initial sources
