# Operation Log (Sample)

> This is a **sample** showing what `memory/log.md` looks like after a quickstart canary run. Yours will live at the repo root as `memory/log.md`.
>
> Append-only chronological record. Format: `## [YYYY-MM-DD] operation | subject`

## [2026-05-19] research | define goal quickstart-pipeline
- Goal: confirm research-flow-template pipeline works end-to-end on Vast.ai
- Issue: GH-N, branch: research/GH-N-quickstart-pipeline
- Seeded goals/quickstart-pipeline.md

## [2026-05-19] vastai | rented RTX_4090 for quickstart-canary
- Instance: 37056539 @ $0.4037/hr (offer 8936966, Iceland)
- SSH key resolved: ~/.ssh/quandang13 (matched registered pubkey quan@maestrolabs.ai)
- Saved state to experiments/.vastai-instance.json

## [2026-05-19] quickstart | executed canary
- Pushed examples/quickstart/train.py via scp
- Launched detached: python train.py, PID 500
- Polled until DONE (1 cycle, ~10s)
- Rsynced results → examples/quickstart/sample-run/

## [2026-05-19] experiment | wrote finding quickstart-pipeline-works
- Source: examples/quickstart/sample-run/results/metrics.json
- Outcome: positive (final_acc=1.0, wall=1.88s, device=cuda)
- Resolves: open-questions/can-pipeline-work-e2e.md

## [2026-05-19] vastai | terminated 37056539 after 0.1h ($0.04)
- Archived state to experiments/.vastai-history.jsonl
- Final sync done before destroy

## [2026-05-19] synthesize | produced outputs/quickstart-synthesis.md
- Consolidated 1 finding into a runbook for future users
- No contradictions (single-finding synthesis)
