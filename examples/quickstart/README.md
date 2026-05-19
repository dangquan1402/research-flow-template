# Quickstart — End-to-End Pipeline Sample

A tiny training run that proves the **rent → ssh → scp → train → sync → report** loop works on your machine + Vast.ai.

## What's here

| File | Purpose |
|---|---|
| `train.py` | 2-layer MLP on synthetic data. Runs ~30s on any GPU (works on CPU too). Writes `results/metrics.json` and `results/loss_curve.csv`. |
| `expected/metrics.json` | Reference output — your run should match within tolerance. |
| `expected/run.log.snippet` | What the training log should look like. |

## Running

Don't run this directly. Follow [`docs/sample-pipeline.md`](../../docs/sample-pipeline.md) — that's the actual walkthrough with verification checkpoints at every step.

## Why this exists

The template's `/vastai`, `/experiment`, `/synthesize`, `/report` skills compose into a long pipeline. Without a concrete sample, a new user can't tell whether step N broke because *they* did something wrong or because the template did. This demo gives a known-good baseline: run it, compare against `expected/`, and if outputs match, the whole pipeline is wired correctly on your machine.
