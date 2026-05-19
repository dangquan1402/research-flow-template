# Sample Run — Real Captured Output

These artifacts come from an **actual run** of the quickstart canary against a real Vast.ai RTX 4090. They serve as the known-good reference: if your own run produces something materially different, the pipeline is broken.

## Provenance

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Vast.ai instance | `37056539` |
| GPU | NVIDIA GeForce RTX 4090 (24 GB) |
| Driver | 565.77 |
| Image | `pytorch/pytorch:latest` (torch 2.2.1, CUDA enabled) |
| Region | Iceland |
| Hourly cost | $0.40/hr |
| Wall time | 1.88 s (training only — total instance time ~5 min including boot, scp, terminate) |
| **Total cost** | **~$0.03** |

## Files

- [`results/metrics.json`](results/metrics.json) — final training metrics
- [`results/loss_curve.csv`](results/loss_curve.csv) — per-epoch loss + accuracy
- [`logs/run.log`](logs/run.log) — full stdout from `nohup python train.py`
- [`logs/run.pid`](logs/run.pid) — PID file (informational)

## How to use

1. Run [`docs/sample-pipeline.md`](../../../docs/sample-pipeline.md) end-to-end yourself.
2. After step 7 (rsync), compare your outputs to these:
   ```bash
   diff <(jq -S . examples/quickstart/results/metrics.json) \
        <(jq -S . examples/quickstart/sample-run/results/metrics.json)
   ```
3. **What should match:**
   - `final_acc == 1.0` (the synthetic data is perfectly separable; anything less means a bug)
   - `epochs == 8`
   - `device == "cuda"` (if you rented a GPU)
4. **What's fine to differ:**
   - `wall_seconds` — depends on GPU type (H100 ≪ 4090 ≪ CPU)
   - `host` — different rental, different hostname
   - `torch_version` — newer images bump it
   - Exact loss values past epoch 1 — non-determinism from CUDA kernels

## Why `final_acc == 1.0` (and isn't that suspicious?)

Yes — and it's intentional. The synthetic data is 10 well-separated Gaussian clusters in 64-d space. The 2-layer MLP solves it in one epoch. **This is a smoke test, not an ML benchmark.** The question being answered is "did data flow through the entire pipeline end-to-end?", not "did the model learn something hard?".

If you want a harder canary, edit `train.py` to make `make_centers` produce overlapping clusters (e.g., `* 1.0` instead of `* 3`) — but then the verify gate changes from `acc == 1.0` to something fuzzier, which is exactly the kind of judgment call you don't want in a canary.

## A real bug this canary caught

The first version of `train.py` shipped with separate random seeds for train and test data — including separate *class centers*. The model overfit to train and got ~7% on test (below the 10% random baseline). The canary surfaced this immediately because `final_acc << 1.0`. The fix is in the current `train.py`: `make_centers` is called once and the result is shared across train/test splits.

That's the value of a runnable canary over hand-crafted "expected" outputs — it actually exercises the code.
