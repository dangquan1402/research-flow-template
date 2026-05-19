---
title: "Finding: research-flow-template pipeline works end-to-end on Vast.ai"
created: 2026-05-19
updated: 2026-05-19
source: examples/quickstart/sample-run/results/metrics.json
confidence: high
verification: source
outcome: positive
tags: [canary, infrastructure, e2e, vastai]
related: [can-pipeline-work-e2e, quickstart-pipeline]
staleness_days: 0
disproves: ""
---

## Insight

The full rent → ssh → scp → train → sync → memory loop documented in `docs/sample-pipeline.md` composes cleanly end-to-end on a real Vast.ai RTX 4090. All 11 verify gates passed without manual fixups beyond user-judgment steps. Total cost: **$0.04** in 6.1 minutes wall time. The canary is now a reliable smoke test for fresh installations.

## Evidence

- Training completed with `final_acc == 1.0` on synthetic data — `examples/quickstart/sample-run/results/metrics.json`
- Per-epoch loss converged from 0.24 to 5.8e-05 across 8 epochs — `examples/quickstart/sample-run/results/loss_curve.csv`
- GPU was correctly detected as CUDA (RTX 4090, torch 2.2.1, driver 565.77) — `examples/quickstart/sample-run/logs/run.log` line 1
- Run-log entry confirms success classification — `experiments/results/run-log.jsonl`
- Total rental cost $0.04 over 6.1 min on offer at $0.40/hr — `experiments/.vastai-history.jsonl`

## Reasoning

The canary's value isn't proving training works (the synthetic data is trivially separable; `acc == 1.0` is a binary signal). Its value is proving each *transport* and *integration* boundary works:

1. `vastai create instance` with `--onstart-cmd "touch /root/.no_auto_tmux"` produces a shell-ready box, not a tmux-hijacked one — confirmed by ssh returning immediately to a prompt
2. The registered Vast.ai pubkey was matched to a local private key (`~/.ssh/quandang13`) and that path was stored in `experiments/.vastai-instance.json` as `ssh_key` for subsequent calls
3. `scp -i <ssh_key> -P <port>` pushed `train.py` and `ssh ... 'ls'` confirmed it landed
4. Detached launch via `(nohup python … &); pgrep | head -1 > run.pid` captured the actual training PID (not the shell wrapper), so polling worked
5. `rsync` pulled `results/` and `logs/` back; `metrics.json` arrived locally with the expected fields

Each of these is a place a green-field user could get stuck. The canary now exercises all of them in one shot.

## Counter-arguments

What would disprove this finding (FUNGI pattern):
- A subsequent fresh-scaffolded project failing the canary would invalidate the "works end-to-end" claim — the finding holds only for the codebase state as of this commit
- Vast.ai changing their `--ssh` semantics (e.g., dropping account-level keys) would break the SSH layer and falsify the "no manual fixups" claim
- A torch image update breaking CUDA detection would falsify the device-detection check
- If the demo data were made harder (overlapping clusters), `acc == 1.0` would no longer be the right verify gate — and the failure mode "did the pipeline run" would conflate with "did the model learn"

## Implications

- The canary is safe to recommend in `docs/getting-started.md` as a setup-verification step
- `/quickstart` skill can rely on `final_acc == 1.0` as a strict gate (not `>= 0.95`)
- A real bug was caught by this canary on first run (train/test seed mismatch in `make_data`) — see commit `c91a53c`. This validates the canary's *purpose*: catching pipeline bugs before they corrupt real research
- The captured artifacts under `examples/quickstart/sample-run/` are the reference users should diff their own runs against
