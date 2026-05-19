---
title: "Synthesis: research-flow-template pipeline canary"
created: 2026-05-19
sources:
  - findings/quickstart-pipeline-works
  - examples/quickstart/sample-run/results/metrics.json
  - experiments/.vastai-history.jsonl
tags: [canary, infrastructure, runbook]
---

# Pipeline Canary — Synthesis

> Output produced by `/synthesize` after a single-finding research cycle. With more findings, this would consolidate themes and contradictions; with one finding, it's a runbook + an honest summary.

## Headline

✅ **The research-flow-template pipeline works end-to-end.** A single Vast.ai RTX 4090 canary completed all 11 verify gates from `docs/sample-pipeline.md` in 6.1 minutes for $0.04. The captured artifacts at `examples/quickstart/sample-run/` are the reference users should diff against.

## What was tested

| Layer | Verification |
|---|---|
| `/research` → branch + issue | Branch `research/GH-N-quickstart-pipeline` created; goal seeded in `goals/` |
| `/vastai rent` | Instance `37056539` (RTX 4090, $0.40/hr, Iceland) up in <30s |
| SSH key resolution | Registered pubkey `quan@maestrolabs.ai` auto-matched to local `~/.ssh/quandang13` |
| SSH transport | `nvidia-smi` returned via non-interactive ssh |
| File transfer | `scp -P` pushed `train.py`; remote `ls` confirmed |
| Detached training | `(nohup … &); pgrep \| head -1` captured PID 500 cleanly |
| Log streaming | `tail` polled without holding a session |
| Result sync | `rsync` pulled `metrics.json` with `final_acc=1.0`, `device=cuda` |
| Memory write | Finding `quickstart-pipeline-works.md` written + index/log updated |
| Synthesis | This document |
| `/vastai terminate` | Instance destroyed; state archived to `.vastai-history.jsonl` |

## Real numbers

```json
{
  "final_acc": 1.0,
  "final_loss": 5.7968499674461785e-05,
  "wall_seconds": 1.88,
  "device": "cuda",
  "torch_version": "2.2.1",
  "host": "9aaa1ec65522",
  "epochs": 8
}
```

Per-epoch loss: 0.2416 → 0.0004 → 0.0002 → 0.0002 → 0.0001 → 0.0001 → 0.0001 → 0.0001
(Synthetic data is fully separable; the model nails it in one epoch and then just keeps shrinking loss.)

## Bug caught by the canary

The first run produced `final_acc ≈ 0.07` (below random for 10 classes). Root cause: `make_data()` in the original `train.py` used different seeds for train and test, and because class centers were derived from the seed, train and test had **disjoint distributions**. Model memorized train, scored noise on test.

Fix shipped in commit `c91a53c`: extract `make_centers()` as a separate function called once, share the result across both splits. Only the noise generators differ by seed now.

**Why this matters for the synthesis:** the canary's purpose isn't to produce `acc=1.0`. Its purpose is to *catch this kind of bug before it pollutes real research*. A canary that always produces a green check without exercising the code is worthless. The fact that the canary failed on first run *and surfaced the failure clearly* is the strongest evidence that it works.

## So what?

1. **For new users:** run `/quickstart` once after `npx create-research-flow`. If `final_acc != 1.0`, stop and read `docs/sample-pipeline.md` — the failure is localized to a specific step.
2. **For template maintainers:** any PR touching `/vastai`, `/quickstart`, or `examples/quickstart/train.py` should re-run the canary before merge. The whole loop is ~$0.05 in 10 minutes.
3. **For real research:** once the canary passes, the user can trust the pipeline and focus on their own training code. Subsequent failures localize to *their* code, not the template.

## Counter-arguments

- This canary tests the *2026-05-19 state* of the template. Vast.ai API changes, image updates, or skill rewrites can invalidate it without notice. **Re-run the canary after upgrading the template.**
- `final_acc == 1.0` is a strict gate that works *because the data is trivially separable*. If anyone makes the demo harder, the gate must loosen to a tolerance, which weakens the binary failure signal.
- Single-finding synthesis is inherently narrow. A future canary suite should test more failure modes (no GPU available, scp permission denied, rsync mid-run interrupted, etc.) before claiming "the pipeline works."

## Next actions

- [ ] (optional) Add `/quickstart --auto` mode that also drives `/vastai rent` and `/vastai terminate` for one-shot CI runs
- [ ] (optional) Distill this finding into a `memory/decisions/use-quickstart-as-canary.md` once the canary is run on ≥3 fresh scaffolds without regressions
- [ ] (out of scope for this canary) Wire `vastai` cost into `experiments/results/run-log.jsonl` automatically on terminate

## Provenance

This synthesis was produced from a real run on 2026-05-19. The exact metrics referenced here are committed at `examples/quickstart/sample-run/results/metrics.json` and `examples/quickstart/sample-run/logs/run.log`. Vast.ai rental record at `experiments/.vastai-history.jsonl`.
