---
name: examples
description: Generate and save concrete worked examples that illustrate key findings and concepts
user_invocable: true
---

# /examples — Generate Worked Examples

## Gather Information

Ask the user for:
1. **Scope** — All findings? Specific concepts or findings?
2. **Audience** (optional) — Technical depth? Who will read these examples?
3. **Format** (optional) — Code examples? Walkthroughs? Annotated traces? Input/output pairs?

## Workflow

### Step 1: Load Context

Read in order:
1. Active goal from `goals/`
2. `memory/index.md`
3. All files in `memory/findings/`
4. All files in `memory/entities/` — concepts that might need examples
5. All files in `memory/themes/`
6. `experiments/` — existing code that can inform examples

### Step 2: Identify What Needs Examples

For each finding, entity, or theme in scope, determine if an example would help:

1. **Abstract claims** — claims about general patterns need concrete instances
2. **Comparative claims** — "X is better than Y" needs a side-by-side example showing both
3. **Process descriptions** — "do A then B" needs a walkthrough with real values
4. **Surprising results** — counter-intuitive findings need examples that make the surprise visible
5. **Key entities/concepts** — important concepts need grounding with concrete instances

Prioritize by:
- How central the concept is to the research goal
- How abstract/hard-to-grasp the claim is without an example
- Whether the claim has counter-arguments (examples help readers evaluate)

### Step 3: Generate Examples

For each item that needs examples, create `outputs/examples/{example-slug}.md`:

```yaml
---
title: "Example: {what this demonstrates}"
created: {today}
finding: {finding-slug or entity-slug}
type: walkthrough | code | comparison | trace | input-output
---

## What This Demonstrates
{1-2 sentences: which finding/concept this example illustrates}

## Setup
{Any context, assumptions, or prerequisites}

## Example
{The actual worked example — detailed, step-by-step, with concrete values}

## What to Notice
{Point out the key aspects that connect back to the finding}

## Variations
{Optional: how would this example change if parameters were different?}
```

**Types of examples:**

**Walkthrough** — Step-by-step trace through a process with real values:
```markdown
### Step 1: Input
Given: 347 + 285

### Step 2: Tokenization (reversed digit-level)
Tokens: [7, 4, 3, +, 5, 8, 2]

### Step 3: Model processes...
{show attention patterns, intermediate states if relevant}

### Step 4: Output
Decoded: [2, 3, 6] → 632 ✓
```

**Code example** — Runnable Python that demonstrates the concept:
Write to `outputs/examples/{example-slug}.py`:
```python
"""
Example: {what this demonstrates}
Finding: {finding-slug}
Run: python outputs/examples/{example-slug}.py
"""
# ... working code that demonstrates the finding ...
```

**Comparison** — Side-by-side showing why one approach wins:
```markdown
| Aspect | Approach A | Approach B |
|--------|-----------|-----------|
| Input  | ...       | ...       |
| Step 1 | ...       | ...       |
| Result | ...       | ...       |
| Why    | {explanation of difference} |
```

**Input/Output pairs** — Concrete examples of expected behavior:
```markdown
| Input | Expected Output | Actual Output | Correct? |
|-------|----------------|---------------|----------|
| 23+45 | 68 | 68 | ✓ |
| 999+1 | 1000 | 1000 | ✓ |
| 347+285 | 632 | 632 | ✓ |
```

**Annotated trace** — Show intermediate values with commentary.

### Step 4: Run Code Examples

For any `.py` examples generated:
```bash
for f in outputs/examples/*.py; do
    echo "=== Running: $f ==="
    python "$f"
    echo ""
done
```

Verify they produce the expected output. Fix any that fail.

### Step 5: Create Examples Index

Write or update `outputs/examples/index.md`:
```yaml
---
title: "Examples Index"
created: {today}
updated: {today}
goal: {goal-slug}
---

## Examples

| # | Example | Finding/Concept | Type | File |
|---|---------|----------------|------|------|
| 1 | {title} | {finding-slug} | {type} | {filename} |
| 2 | ... | ... | ... | ... |
```

### Step 6: Link Examples Back to Findings

For each finding/entity that now has examples:
- Update the file to add an `## Examples` section:
```markdown
## Examples
- [{example-title}](../../outputs/examples/{filename}) — {description}
```

### Step 7: Update Memory Log

Append to `memory/log.md`:
```
## [{today}] examples | {scope-description}
- Examples generated: {count}
- Types: {walkthrough_count} walkthroughs, {code_count} code, {comparison_count} comparisons, {io_count} I/O pairs
- Findings illustrated: {list}
- Branch: {current-branch}
```

### Step 8: Commit

```bash
git add outputs/examples/ memory/
git commit -m "{type}({scope}): generate examples — {count} examples for {finding_count} findings"
git push
```

## Output

Report to user:
- List of examples generated (with file paths)
- Which findings/concepts now have concrete illustrations
- Which important concepts still lack examples
- Any code examples that failed to run (need fixing)
