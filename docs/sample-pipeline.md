---
layout: default
title: Sample Pipeline (Quickstart)
nav_order: 4
---

# Sample Pipeline — End-to-End on Vast.ai
{: .no_toc }

A 15-minute walkthrough that runs the full **rent → ssh → scp → train → sync → report** loop using the bundled `examples/quickstart/` demo. Total Vast.ai cost: **~$0.20** on a cheap GPU.

Every step has a **✅ Verify** checkpoint. If your output matches, that step is working. If it doesn't, fix that step before continuing — don't push forward and debug five layers deep.

> **Shortcut:** once you've done steps 1–2 (define goal, rent GPU), run `/quickstart` to automate the mechanical steps 3–8 (ssh smoke test, scp, launch, poll, rsync, log). It stops before `/experiment` so you stay in the loop on the judgment calls. This walkthrough is the long-form version that explains what `/quickstart` is doing.

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## Why this exists

The template's skills (`/vastai`, `/experiment`, `/synthesize`, `/report`) compose into a long pipeline. Without a known-good sample, you can't tell whether step N is broken because of your setup, the template, or the GPU. This walkthrough is the **canary**: if it runs clean end-to-end, your installation is wired correctly.

What you'll produce:
- A trained model with `final_acc >= 0.95` on synthetic data
- `experiments/results/run-log.jsonl` entry
- `memory/findings/quickstart-pipeline-works.md`
- `outputs/quickstart-report.html`

---

## Prerequisites

You should have already completed [Getting Started](getting-started.md):
- Claude Code installed and logged in
- `uv sync` ran successfully
- `vastai` CLI installed, API key set, SSH key registered
- GitHub repo + project board created

Sanity check:

```bash
which vastai && vastai show ssh-keys | head -3
```

✅ **Verify:** prints a path to `vastai` and at least one SSH key listed.

---

## Step 1 — Define the research goal

Inside Claude Code:

```
/research
```

When prompted, paste:

> **Goal:** Confirm the research-flow-template pipeline works end-to-end by training a tiny model on Vast.ai and producing a report.

Claude will create a GitHub issue, branch (`research/GH-N-quickstart-pipeline`), and seed `goals/quickstart-pipeline.md`.

✅ **Verify:**
```bash
git branch --show-current      # starts with research/GH-
ls goals/                      # contains quickstart-pipeline.md
gh issue list --label research-goal
```

---

## Step 2 — Rent a GPU

```
/vastai rent
```

Answer the prompts:
- **GPU:** `RTX 4090` (cheapest option that works) or `H100` if you want speed
- **Disk:** `20` GB
- **Image:** `pytorch/pytorch:latest`
- **Jupyter:** no (we drive it via SSH only)
- **Expected runtime:** ~5 minutes

Claude runs `vastai search offers ...`, shows top 5, and creates the instance with `--onstart-cmd "touch /root/.no_auto_tmux && mkdir -p /workspace"`.

✅ **Verify:**
```bash
cat experiments/.vastai-instance.json
```
Should print JSON with `id`, `ssh_host`, `ssh_port`, `dph`. Billing has started — note the `dph` (dollars per hour).

```bash
vastai show instances
```
The new instance should be `running` (not `loading`).

---

## Step 3 — Test the SSH connection

Ask Claude:

> Run `nvidia-smi` on the rented instance.

Claude reads `.vastai-instance.json` and runs:

```bash
ssh -p <port> -o StrictHostKeyChecking=accept-new root@<host> 'nvidia-smi'
```

✅ **Verify:** output shows the GPU name (`RTX 4090` / `H100`), driver version, and CUDA version. If you get `Permission denied (publickey)`, your account-level SSH key wasn't applied — run `vastai attach ssh <id> "$(cat ~/.ssh/id_ed25519.pub)"` and retry.

---

## Step 4 — Push the training script (scp)

```bash
scp -P <port> examples/quickstart/train.py root@<host>:/workspace/train.py
```

(Note **uppercase `-P`** for scp — Vast.ai gotcha.)

✅ **Verify:**
```bash
ssh -p <port> root@<host> 'ls -la /workspace/'
```
Should show `train.py` with non-zero size.

---

## Step 5 — Launch training detached

```bash
ssh -p <port> root@<host> << 'EOF'
cd /workspace
mkdir -p logs results
nohup python train.py > logs/run.log 2>&1 &
echo $! > logs/run.pid
echo "Started PID: $(cat logs/run.pid)"
EOF
```

The SSH call returns immediately with the PID. Training is now detached on the box — your laptop can sleep, the run continues.

✅ **Verify:**
```bash
ssh -p <port> root@<host> 'kill -0 $(cat /workspace/logs/run.pid) && echo RUNNING'
```
Prints `RUNNING`.

---

## Step 6 — Poll logs while it trains

Ask Claude:

> Tail the training log every 15s until done.

Or manually:

```bash
ssh -p <port> root@<host> 'tail -n 20 /workspace/logs/run.log'
```

✅ **Verify:** within ~30s you should see lines like:

```
[quickstart] device=cuda torch=2.4.0 host=C.12345678
[quickstart] epoch=1/8 loss=1.4231 acc=0.7320
...
[quickstart] epoch=8/8 loss=0.0456 acc=0.9910
[quickstart] done in 12.4s  final_acc=0.9910  → results/metrics.json
```

Compare against [`examples/quickstart/expected/run.log.snippet`](../examples/quickstart/expected/run.log.snippet). The exact numbers will vary but the shape should match.

When you see `done in Xs`, the process has exited.

---

## Step 7 — Pull results back (rsync)

```bash
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/results/ examples/quickstart/results/
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/logs/    examples/quickstart/logs/
```

✅ **Verify:**
```bash
cat examples/quickstart/results/metrics.json
```
Should show `final_acc >= 0.95`, `device: "cuda"`, plus host/torch version. Compare against `examples/quickstart/expected/metrics.json`.

If `final_acc < 0.95`, training got cut off — check the log for an early exit.

---

## Step 8 — Log the run

Append to `experiments/results/run-log.jsonl`:

```bash
echo '{"date":"'"$(date -u +%Y-%m-%d)"'","experiment":"quickstart","status":"success","notes":"E2E pipeline canary on Vast.ai. See examples/quickstart/results/metrics.json"}' \
  >> experiments/results/run-log.jsonl
```

Or just ask Claude:

> Append a success entry for `quickstart` to `experiments/results/run-log.jsonl`.

✅ **Verify:** `tail -n 1 experiments/results/run-log.jsonl` shows your entry.

---

## Step 9 — Write the finding

```
/experiment
```

When asked, point Claude at `examples/quickstart/results/metrics.json` and tell it:

> The hypothesis was "the pipeline works end-to-end." The acceptance criterion was `final_acc >= 0.95`. Write a positive finding.

Claude writes `memory/findings/quickstart-pipeline-works.md` with citation back to the metrics file, updates `memory/index.md`, and appends to `memory/log.md`.

✅ **Verify:**
```bash
ls memory/findings/ | grep quickstart
grep -l quickstart memory/index.md
tail -n 3 memory/log.md
```
All three should hit.

---

## Step 10 — Synthesize and report

```
/synthesize
/report                # if you've added the /report skill; otherwise /synthesize already drops outputs/synthesis-*.md
```

✅ **Verify:**
```bash
ls outputs/
```
Should contain a synthesis markdown file (and an HTML report if `/report` exists) referencing the quickstart finding.

---

## Step 11 — Terminate and check cost

```
/vastai terminate
```

Claude offers a final rsync (already done in step 7), then runs `vastai destroy instance <id>`. State moves from `.vastai-instance.json` → `.vastai-history.jsonl`.

✅ **Verify:**
```bash
test ! -f experiments/.vastai-instance.json && echo "cleaned up"
tail -n 1 experiments/.vastai-history.jsonl
```
The history line should show total uptime and cost (typically $0.10–$0.30 for this walkthrough).

---

## Smoke-test summary

If all 11 ✅ Verify checks passed, your pipeline is wired correctly:

| Layer | What was proven |
|---|---|
| Goal → branch → issue | `/research` creates GitHub artifacts |
| Vast.ai rental | API key + SSH key + `--onstart-cmd` tmux disable all work |
| SSH transport | Non-interactive `ssh` returns output cleanly |
| File transfer | `scp -P` and `rsync` push/pull both work |
| Detached training | `nohup … &` survives the SSH disconnect |
| Log streaming | Agent can poll logs without holding a session |
| Result sync | `metrics.json` arrives locally with sane values |
| Memory layer | `/experiment` writes finding + updates index/log |
| Synthesis | `/synthesize` reads memory and produces output |
| Cleanup | `/vastai terminate` releases the box and archives state |

If any check failed, **stop there** and fix that layer before continuing. The whole point of this canary is to localize failures.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Permission denied (publickey)` on first SSH | Account key was added *after* the instance was created | `vastai attach ssh <id> "$(cat ~/.ssh/id_ed25519.pub)"` |
| SSH hangs / drops into tmux | Forgot `touch /root/.no_auto_tmux` in `--onstart-cmd` | Recreate the instance with the flag set |
| `train.py: command not found` | Pushed to wrong dir | Confirm with `ssh ... 'ls /workspace'` |
| `nvidia-smi` works but training reports `device=cpu` | Image doesn't have CUDA torch | Use `pytorch/pytorch:latest` (not generic `python:3.11`) |
| `Host key verification failed` | Reusing a host:port from a prior rental | `ssh-keygen -R "[host]:port"` and retry |
| Costs higher than ~$0.30 | Forgot to terminate, or chose H100 instead of 4090 | `/vastai terminate` immediately; check `vastai show instances` |
