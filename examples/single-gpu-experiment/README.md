# Single GPU Experiment — Establishing a Tiny-Transformer Baseline

A narrated walkthrough of one real research question taken end-to-end with the
template: define question → rent GPU → write script → train → sync → write up
finding → terminate. Total cost on Vast.ai: **~$0.15** on an RTX 4090.

Unlike [`examples/quickstart/`](../quickstart/) — which is a synthetic canary
that proves the pipeline *plumbing* works — this example produces a **real
research artifact** (a measured baseline) that future hypothesis branches can
compare against.

The flow below alternates between **what you (the human) type** and **what
Claude does in response**. Tool calls are paraphrased for readability; the
actual session has more detail.

---

## The question

> Train a small char-level transformer on Tiny Shakespeare. How low can val loss
> go in 2000 steps on a single GPU, holding a sensible default config? Record
> the number as a baseline so later experiments (deeper, wider, different LR
> schedule, etc.) have something to beat.

Acceptance criterion: a logged `metrics.json` with `best_val_loss` recorded,
and a `memory/findings/` entry citing it.

---

## 1. Frame the goal

**You:**
> /research
>
> Goal: establish a baseline val-loss for a tiny char-transformer on Tiny
> Shakespeare. Single-GPU, ~10 min on a 4090. Output a measured baseline that
> future hypothesis branches can compare against.

**Claude:**
- Creates GitHub issue (label `research-goal`)
- Creates branch `research/GH-<n>-tiny-transformer-baseline`
- Seeds `goals/tiny-transformer-baseline.md` with the question + acceptance
  criterion
- Adds the issue to the project board

✅ **Verify:** `git branch --show-current` starts with `research/GH-`.

---

## 2. Sketch the experiment together

**You:**
> Before we write any code — what's the right model size to use as a baseline?
> I want something small enough that a 4090 finishes in <10 min but big enough
> that the loss curve is actually informative.

**Claude:** suggests 4 layers / 4 heads / 128-dim / context 128 / batch 64 —
roughly 0.8M params. Cites that nanoGPT's "shakespeare_char" config is in the
same ballpark and trains in a few minutes on a single 4090.

**You:**
> Good. Use AdamW with cosine LR, 100-step warmup, 2000 total steps. Write
> `train.py` self-contained — download Tiny Shakespeare on first run, no
> external prep step.

**Claude:** writes [`train.py`](train.py). One file, downloads the corpus on
first run, writes `results/metrics.json` and `results/loss_curve.csv`. About
200 lines.

✅ **Verify:** `python train.py` runs locally on CPU in a few minutes if you
want to sanity-check the script before paying for a GPU. Output should show
`device=cpu` and val loss still descending — slower, but the curve shape is
the same.

---

## 3. Rent the GPU (with cost guardrails)

Before paying for anything, confirm the account-level safety net is in place.
This is a one-time setup — skip if you've done it already.

**You (in browser):** open https://cloud.vast.ai/billing/, **turn autobilling
OFF**, and keep your loaded balance low (say $10). With autobilling on, your
card auto-tops-up — there is no spending ceiling. With it off, your balance
is the hard cap.

Now back in Claude Code:

**You:**
> /vastai rent
>
> 4090, 20GB disk, pytorch/pytorch:latest image, no jupyter.
> Guardrails: dph_max=$0.40/hr, runtime_minutes=10 (training is ~5 min, give 2× margin → --max-seconds=1200).

**Claude:**
- Shows projected cost: `$0.40 × 10/60 = $0.07` if it runs the full expected window at the cap rate
- Reminds you that the *hard* ceiling is your account balance (autobilling OFF) — Vast.ai has no per-instance auto-stop, so wall-clock discipline lives in the training script
- Runs `vastai search offers 'reliability>0.95 num_gpus=1 gpu_name=RTX_4090 dph<0.40' --order dph_total --limit 5`
- Picks the cheapest verified host and creates the instance with
  `--onstart-cmd "touch /root/.no_auto_tmux && mkdir -p /workspace"`
- Writes `experiments/.vastai-instance.json` with `id`, `ssh_host`,
  `ssh_port`, `ssh_key`, `dph`, and a `guardrails` block (`dph_max`,
  `runtime_minutes`, `max_seconds_arg`, `projected_usd`)

If the search returns 0 offers, **Claude won't silently widen the filter** —
it'll ask whether you want to raise `dph_max`. That's by design.

✅ **Verify:**
```bash
cat experiments/.vastai-instance.json | jq '{id, dph, ssh_host, guardrails}'
vastai show instances     # should say "running"
```
The `guardrails.max_seconds_arg` value (`1200` in this example) is what gets
passed to `train.py --max-seconds 1200` in step 6 — that's where the
wall-clock cap actually lives. Vast.ai itself does not enforce one.

---

## 4. SSH smoke test

**You:**
> nvidia-smi on the box.

**Claude:** reads `.vastai-instance.json`, runs:
```bash
ssh -i <ssh_key> -p <port> -o StrictHostKeyChecking=accept-new root@<host> 'nvidia-smi'
```

✅ **Verify:** GPU name (`NVIDIA GeForce RTX 4090`), driver, CUDA version all
print. If you see `Permission denied (publickey)`, see the
[troubleshooting table in sample-pipeline.md](../../docs/sample-pipeline.md#troubleshooting).

---

## 5. Push the script

**You:**
> scp train.py over.

**Claude:**
```bash
scp -i <ssh_key> -P <port> examples/single-gpu-experiment/train.py \
  root@<host>:/workspace/train.py
```

(Capital `-P` for scp — Vast.ai gotcha.)

✅ **Verify:** `ssh ... 'ls -la /workspace/'` shows `train.py` non-zero size.

---

## 6. Launch detached

**You:**
> kick it off in the background, log to /workspace/logs/run.log

**Claude:**
```bash
ssh -i <ssh_key> -p <port> root@<host> << 'EOF'
cd /workspace
mkdir -p logs results
nohup python train.py --max-seconds 1200 > logs/run.log 2>&1 &
echo $! > logs/run.pid
echo "Started PID: $(cat logs/run.pid)"
EOF
```

SSH returns immediately. Training runs detached — your laptop can sleep.
The `--max-seconds 1200` flag is the script-side wall-clock cap: even if the
loss explodes or the loop hangs, the process exits cleanly after 20 minutes.
That's the only wall-clock cap that actually fires — Vast.ai has no
equivalent server-side feature.

✅ **Verify:**
```bash
ssh -i <ssh_key> -p <port> root@<host> 'kill -0 $(cat /workspace/logs/run.pid) && echo RUNNING'
```

---

## 7. Poll until done

**You:**
> tail the log every 30s until it prints "done in"

**Claude:** loops `ssh ... 'tail -n 5 /workspace/logs/run.log'` every 30
seconds, stops when it sees the `done in` marker.

✅ **Verify:** log lines look like:
```
[baseline] step=100/2000 train_loss=2.5189 val_loss=2.5044 lr=0.00030
...
[baseline] step=2000/2000 train_loss=1.5388 val_loss=1.6234 lr=0.00000
[baseline] done in 184.7s  best_val=1.6201  final_val=1.6234  → results/metrics.json
```

Compare against [`sample-run/run.log`](sample-run/run.log). Your numbers
should land within a few percent — the seed is fixed, but cuDNN
non-determinism will move things slightly.

---

## 8. Pull results back

**You:**
> rsync results to examples/single-gpu-experiment/results/

**Claude:**
```bash
rsync -avz -e "ssh -i <ssh_key> -p <port>" \
  root@<host>:/workspace/results/ \
  examples/single-gpu-experiment/results/
rsync -avz -e "ssh -i <ssh_key> -p <port>" \
  root@<host>:/workspace/logs/ \
  examples/single-gpu-experiment/logs/
```

✅ **Verify:**
```bash
cat examples/single-gpu-experiment/results/metrics.json | jq '.best_val_loss, .device'
```
Should show `~1.62` and `"cuda"`. Compare against
[`expected/metrics.json`](expected/metrics.json) — within ~0.05 is fine.

---

## 9. Log the run

**You:**
> append a success entry for `tiny-transformer-baseline` to the run log

**Claude:**
```bash
echo '{"date":"'"$(date -u +%Y-%m-%d)"'","experiment":"tiny-transformer-baseline","status":"success","notes":"best_val_loss=1.6201 on RTX 4090, 184s. See examples/single-gpu-experiment/results/metrics.json"}' \
  >> experiments/results/run-log.jsonl
```

---

## 10. Write the finding

**You:**
> /experiment
>
> Hypothesis: a 4-layer, 128-dim char-transformer can reach val loss < 1.7 on
> Tiny Shakespeare in 2000 steps. Acceptance: best_val_loss < 1.7. Cite
> examples/single-gpu-experiment/results/metrics.json. Write a positive
> finding — this is our baseline number.

**Claude:**
- Creates `memory/findings/tiny-transformer-shakespeare-baseline.md` with the
  hypothesis, the measured number (`best_val_loss=1.6201`), the hparams, and
  a citation to `metrics.json`
- Adds a **FUNGI counter-argument**: "What would disprove this as a baseline?
  — A different seed giving a substantially different number, or a
  non-converged run that just happened to bottom out at 1.62." Marks
  confidence `medium` until reproduced.
- Updates `memory/index.md` (new finding listed)
- Appends to `memory/log.md`:
  `## [YYYY-MM-DD] experiment | tiny-transformer-baseline → finding`
- Creates a GitHub sub-issue with label `finding`, linked to the parent

✅ **Verify:**
```bash
ls memory/findings/ | grep tiny-transformer
grep tiny-transformer memory/index.md
tail -n 3 memory/log.md
gh issue list --label finding
```

---

## 11. Terminate

**You:**
> /vastai terminate

**Claude:**
- Offers a final rsync (already done in step 8 — declines unless something
  changed)
- Runs `vastai destroy instance <id>`
- Moves `.vastai-instance.json` → appends a line to `.vastai-history.jsonl`
  with total uptime + cost
- **Guardrail post-mortem:** compares actual spend vs `projected_usd`. If
  `total_cost > 3 × projected_usd`, flags loudly: "Box stayed up much longer
  than the expected runtime — lower `runtime_minutes` next time or terminate
  sooner."

✅ **Verify:**
```bash
test ! -f experiments/.vastai-instance.json && echo "cleaned up"
tail -n 1 experiments/.vastai-history.jsonl
```
Cost should be **$0.05–$0.15** for this experiment — well in line with the
$0.07 projection from step 3.

---

## What you should now have

| Artifact | Path |
|---|---|
| Goal | `goals/tiny-transformer-baseline.md` |
| Code | `examples/single-gpu-experiment/train.py` |
| Metrics | `examples/single-gpu-experiment/results/metrics.json` |
| Loss curve | `examples/single-gpu-experiment/results/loss_curve.csv` |
| Log | `examples/single-gpu-experiment/logs/run.log` |
| Run-log entry | line in `experiments/results/run-log.jsonl` |
| Finding | `memory/findings/tiny-transformer-shakespeare-baseline.md` |
| GitHub | parent issue + finding sub-issue, both on project board |

The baseline is now **citable** from any future hypothesis branch. When you
later try "what if I double the depth," your finding can say
*"baseline = 1.6201 (see [tiny-transformer-shakespeare-baseline]); depth-8
variant = X.XX, delta = ..."* — and that's the moment the wiki-style memory
layer pays off.

---

## Patterns this example demonstrates

These are the human↔Claude interaction patterns worth internalizing:

1. **Drop the goal in plain language, then let `/research` formalize it.** Don't
   pre-write the GitHub issue body — Claude does that.
2. **Negotiate the hyperparameters in chat before writing code.** Sketching
   model size / steps / optimizer as a back-and-forth is cheaper than rewriting
   the script three times.
3. **Always sanity-run on CPU first** if the script is new. It catches
   tensor-shape bugs without burning GPU minutes.
4. **Detached launch + polling, not interactive sessions.** `nohup ... &` plus
   `tail` is what lets your laptop sleep.
5. **The finding cites the artifact, not the chat.** `metrics.json` is the
   ground truth; the finding is interpretation. Both are checked in.
6. **Terminate immediately.** Cost discipline starts the moment the run
   finishes. Don't "leave it up for later."
7. **Set guardrails before searching offers, not after.** `dph_max` goes into
   the `vastai search offers` filter. The wall-clock cap lives in the
   training script (`--max-seconds`), not in Vast.ai — there's no server-side
   auto-stop. Combined with autobilling OFF (the only true server-side
   ceiling) you get a layered defense. See [`.claude/skills/vastai.md` § Cost Guardrails](../../.claude/skills/vastai.md#cost-guardrails)
   for the full model, including a list of things that look like guardrails
   but aren't.

---

## Troubleshooting

The pipeline-level failure modes are the same as in
[`docs/sample-pipeline.md` § Troubleshooting](../../docs/sample-pipeline.md#troubleshooting).
Experiment-specific issues:

| Symptom | Likely cause | Fix |
|---|---|---|
| `best_val_loss > 2.0` | Training didn't converge — wrong device, NaN loss, bad seed | Check `metrics.json.device == "cuda"`; inspect `loss_curve.csv` for divergence |
| `val_loss < train_loss` consistently | Eval batches too small (noisy) | Increase `EVAL_BATCHES` in `train.py` |
| Wall time > 10 min on a 4090 | Wrong GPU rented, or CPU fallback | Confirm `nvidia-smi` shows the 4090 *and* `metrics.json.device == "cuda"` |
| Download hang on first run | Outbound HTTPS blocked on the box | Pre-stage `input.txt` and `scp` it alongside `train.py` |
| `vastai search offers` returns 0 results | `dph_max` too tight for the chosen GPU | Ask Claude to raise the cap (e.g., `dph<0.60`). Don't drop the filter entirely — that's what it's there for. |
| Final cost > 3× projected | Box stayed up much longer than expected runtime | Surfaced by the `terminate` post-mortem. Lower `runtime_minutes` next time, terminate sooner, and double-check `--max-seconds` is actually being passed to the training script. |
