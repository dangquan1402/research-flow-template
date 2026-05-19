---
title: "Open Question: Can the pipeline run cleanly end-to-end on real Vast.ai?"
created: 2026-05-19
updated: 2026-05-19
source: analysis
confidence: medium
verification: gap
tags: [canary, infrastructure]
related: [quickstart-pipeline]
staleness_days: 0
---

## Question

Does the rent → ssh → scp → train → sync → memory loop, as documented in `docs/sample-pipeline.md`, actually compose end-to-end without manual fixups when run against a real Vast.ai GPU?

## Why we don't know yet

The skills (`/vastai`, `/quickstart`) and the demo (`examples/quickstart/train.py`) were written without an integration run. Each layer was reasoned about in isolation. Common failure modes that won't surface until a real run:

- SSH key indirection (registered Vast.ai key ≠ local SSH default)
- Bash precedence bugs in detached-launch commands (`mkdir && nohup … &` race)
- Data-loading bugs in the demo (e.g., train/test distribution mismatch)
- Vast.ai image gotchas (missing torch, missing CUDA, tmux hijack)

## What would close this question

A single end-to-end run that hits every step in `docs/sample-pipeline.md` and produces a `metrics.json` with `final_acc == 1.0`. Anything less means a real bug in one of the layers.

## Resolved by

`memory/findings/quickstart-pipeline-works.md` (2026-05-19) — answered after the actual run on instance `37056539`.
