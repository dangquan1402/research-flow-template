# Memory Page Template

All memory pages (entities, findings, themes, open-questions) use this frontmatter:

```yaml
---
title: "Page Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: source-slug or "analysis"
confidence: high | medium | low
verification: source | analysis | unverified | gap
tags: [tag1, tag2]
related: [other-page-slug]
staleness_days: 0
---
```

## Field Definitions

- **confidence**: How sure we are about the content
  - `high` — directly cited from primary source
  - `medium` — inferred from multiple sources or strong analysis
  - `low` — speculative, single weak source, or outdated
- **verification** (Verification Gates pattern):
  - `source` — claim is directly cited with reference
  - `analysis` — inference is shown with reasoning chain
  - `unverified` — noted but not yet validated
  - `gap` — explicitly identified as missing information
- **staleness_days**: Auto-incremented by lint. Reset to 0 when page is re-validated.
- **related**: Cross-references to other memory pages (by filename slug)

## Finding Template

```markdown
---
title: "Finding: [Concise insight]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: source-slug
confidence: medium
verification: analysis
tags: []
related: []
staleness_days: 0
disproves: ""
---

## Insight

[One-paragraph summary of the finding]

## Evidence

- [Citation or data point 1] — [source-slug]
- [Citation or data point 2] — [source-slug]

## Reasoning

[How the evidence leads to this conclusion]

## Counter-arguments

[What would disprove this? — FUNGI pattern]

## Implications

[What this means for the research goal]
```

## Entity Template

```markdown
---
title: "Entity: [Name]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: source-slug
confidence: high
verification: source
tags: []
related: []
staleness_days: 0
type: person | org | concept | tool | paper
aliases: []
---

## Description

[What/who this entity is]

## Relevance

[Why this entity matters to the research goal]

## Key Facts

- [Fact 1] — [source]
- [Fact 2] — [source]

## Connections

- Related to [other-entity] because [reason]
```

## Negative Finding Template

For experiments that completed but did not meet acceptance criteria:

```yaml
---
title: "Negative Result: [What failed and why]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: experiments/results/{result-file}.json
confidence: high
verification: source
outcome: negative
tags: [experiment, negative-result, ...]
related: []
staleness_days: 0
---

## Insight

[What we expected vs what happened]

## Evidence

[The actual numbers — accuracy, loss, training curves]

## Why It Failed

[Root cause analysis — was the hypothesis wrong, or was the test wrong?]

## What This Rules Out

[What we can now confidently NOT pursue]

## What This Suggests Instead

[Redirect — what should we try next?]

## Counter-arguments

[What would disprove this negative conclusion?]
```

## Decision Record Template

For distilled decisions backed by multiple experiment findings:

```yaml
---
title: "Decision: [Concise actionable statement]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
supersedes: null
evidence:
  - finding-slug-1
  - finding-slug-2
config: baselines/config-name.yaml
tags: [architecture, training, data]
---

## Decision

[One-sentence actionable statement]

## Rationale

[Summary of evidence from linked findings]

## Tradeoffs Accepted

[What we gave up and why it is acceptable]

## Revert Conditions

[Under what circumstances this decision should be revisited]
```

## Theme Template

```markdown
---
title: "Theme: [Pattern name]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: analysis
confidence: medium
verification: analysis
tags: []
synthesizes: [finding-1, finding-2, finding-3]
staleness_days: 0
---

## Pattern

[Description of the cross-cutting pattern]

## Supporting Findings

- [finding-slug-1]: [how it supports]
- [finding-slug-2]: [how it supports]

## Contradictions

[Any findings that tension with this theme]

## Counter-arguments

[What would disprove this theme? — FUNGI pattern]

## So What?

[What this theme means for the research goal — actionable implications]
```
