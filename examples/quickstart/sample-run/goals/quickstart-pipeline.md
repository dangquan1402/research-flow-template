---
title: "Goal: Confirm research-flow-template pipeline works end-to-end"
created: 2026-05-19
updated: 2026-05-19
status: complete
issue: GH-N
branch: research/GH-N-quickstart-pipeline
tags: [canary, infrastructure, e2e]
---

## Question

Does the full research-flow-template pipeline (rent GPU → ssh → scp → train → sync → memory → synthesis) run cleanly end-to-end on a freshly-scaffolded project?

## Why this matters

A new researcher dropping into a freshly-scaffolded `research-flow-template` project has no way to distinguish, when something breaks, between:
- their local setup (Python, SSH keys, vastai CLI)
- the Vast.ai layer (rental, GPU drivers, image)
- the template's own skills (`/vastai`, `/quickstart`, `/experiment`, `/synthesize`)
- their actual research code

A known-good canary localizes failures: if it passes, the pipeline is wired correctly and any subsequent failure belongs to *their* code, not the template.

## Success criteria

- [ ] All 11 ✅ Verify gates in `docs/sample-pipeline.md` pass on a real Vast.ai RTX 4090
- [ ] `experiments/results/run-log.jsonl` gains a `success` entry for `quickstart`
- [ ] A finding is written into `memory/findings/` citing the captured `metrics.json`
- [ ] A synthesis report is produced under `outputs/`
- [ ] Total cost stays under $1

## Scope (in / out)

**In:** verifying the rental, transport, training, sync, and memory layers all compose without manual intervention beyond user-judgment steps.

**Out:** training a model that learns something hard. The demo uses fully-separable synthetic data on purpose — `final_acc == 1.0` is a binary signal (works / doesn't), not a benchmark score.

## Status

Complete (2026-05-19). All 11 gates passed on instance `37056539` (RTX 4090, $0.04, 6.1 min). See `memory/findings/quickstart-pipeline-works.md` for the result.
