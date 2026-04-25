# Experiment Config Schema

YAML experiment definitions that map to CLI args for `python -m experiments.train`.

## Single Experiment Config

```yaml
meta:                           # Metadata (not passed to trainer)
  name: "descriptive-name"      # Used as --tag if no tag specified
  question: "open-question-slug" # Links to memory/open-questions/
  hypothesis: "What we expect"
  acceptance_criteria: ">99% accuracy on 5-digit addition"
  tags: ["baseline", "verified"]

task:                           # Maps to --op, --max_digits, etc.
  op: add                       # add | sub | mul | mixed
  max_digits: 5
  tokenizer: reversed           # reversed | plain
  balanced_carry: true
  scratchpad: false
  pos_encoding: learned         # learned | position_coupling
  eval_max_digits: null         # Set for OOD evaluation

architecture:                   # Maps to --architecture, --n_layers, etc.
  architecture: decoder_only    # decoder_only | looped | encoder_decoder
  n_layers: 2
  n_heads: 4
  dim: 384
  ff_dim: 1536
  activation: gelu              # gelu | swiglu | relu_squared
  n_loops: 4                    # Only for looped architecture

training:                       # Maps to --epochs, --lr, etc.
  epochs: 50
  batch_size: 256
  lr: 0.001
  weight_decay: 0.5
  warmup_steps: 100
  train_samples: 50000
  test_samples: 2000
  eval_every: 5
  seed: 42

mlflow:                         # MLflow tracking
  enabled: true
  experiment: "experiment-name"
  mlflow_tracking_uri: "file:./mlruns"
```

## Sweep Config

For running multiple variants from a shared base:

```yaml
meta:
  name: "sweep-name"
  question: "open-question-slug"

base:                           # Shared params across all runs
  task: { ... }
  training: { ... }
  mlflow: { enabled: true, experiment: "sweep-name" }

runs:                           # Each run overrides base
  - name: "variant-1"
    architecture: { n_layers: 2, dim: 384 }
  - name: "variant-2"
    architecture: { n_layers: 4, dim: 256 }
```

## Running

```bash
# Single experiment
uv run python -m experiments.run experiments/configs/baselines/add-5d-reversed-2L384D.yaml

# Sweep
uv run python -m experiments.run experiments/configs/sweeps/depth-vs-width.yaml

# Batch (all baselines)
uv run python -m experiments.run experiments/configs/baselines/*.yaml

# Dry run (print configs without training)
uv run python -m experiments.run --dry-run experiments/configs/baselines/*.yaml
```

## Failure Classification

Results in `experiments/results/run-log.jsonl` use these status codes:

| Status | Meaning | Action |
|--------|---------|--------|
| `success` | Ran to completion, met acceptance criteria | Write finding, update question |
| `partial` | Completed but missed acceptance criteria | Negative finding + next iteration |
| `inconclusive` | Results ambiguous (needs more epochs, etc.) | Record, may re-run |
| `failed:config` | Crashed due to bad config (shape mismatch, OOM) | Fix config, re-run |
| `failed:bug` | Crashed due to code bug | Fix bug, re-run |
| `failed:infra` | Crashed due to infrastructure (disk, memory) | Re-run later |

## Directory Structure

```
configs/
  baselines/     # Known-good verified configs (backed by decision records)
  sweeps/        # Multi-run sweep definitions
  README.md      # This file
```
