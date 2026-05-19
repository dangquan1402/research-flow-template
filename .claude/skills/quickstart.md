---
name: quickstart
description: Run the end-to-end pipeline canary on Vast.ai using the bundled examples/quickstart/ demo. Automates the mechanical shell steps (push code, launch detached, poll, sync, log) and stops at user-judgment steps so the human stays in the loop.
user_invocable: true
---

# /quickstart — Pipeline Canary

Drives the [`docs/sample-pipeline.md`](../../docs/sample-pipeline.md) walkthrough end-to-end. **Purpose: prove the rent → ssh → scp → train → sync → report pipeline works on this machine.** Not for real research.

## When to use

- First time setting up the template on a new machine
- After upgrading `vastai`, torch, or any pipeline-touching dep
- After changing any skill in `.claude/skills/`
- When debugging a failed real experiment and you need to isolate whether the pipeline itself is broken

## What this skill does and does NOT do

| Step | Automated? | Why |
|---|---|---|
| 1. `/research` | ❌ — defer to user | Goal definition is a user-judgment call |
| 2. `/vastai rent` | ❌ — defer to user | Costs money, GPU choice is user's call |
| 3. SSH smoke test | ✅ | Pure verification |
| 4. `scp train.py` | ✅ | Mechanical |
| 5. Launch detached | ✅ | Mechanical |
| 6. Poll logs | ✅ | Mechanical |
| 7. Rsync results | ✅ | Mechanical |
| 8. Append run-log entry | ✅ | Mechanical |
| 9. `/experiment` finding | ❌ — defer to user | Classification is a judgment call |
| 10. `/synthesize` | ❌ — defer to user | User triggers when ready |
| 11. `/vastai terminate` | ❌ — defer to user | Costs control belongs to user |

## Preconditions (check, don't run)

Before doing anything, verify the user has completed steps 1-2 manually:

```bash
git branch --show-current        # must start with research/
test -f experiments/.vastai-instance.json && echo "instance: yes" || echo "instance: NO"
test -f examples/quickstart/train.py && echo "demo: yes" || echo "demo: NO"
```

If any check fails, **stop and tell the user**:
- No research branch → "Run `/research` first to define a goal and create a branch."
- No `.vastai-instance.json` → "Run `/vastai rent` first (RTX 4090, 20GB disk, pytorch/pytorch:latest)."
- No `train.py` → "The quickstart demo is missing — this template wasn't scaffolded correctly. Reinstall via `npx create-research-flow`."

Do **not** attempt to run these steps yourself — they require user input and money.

## Workflow

### Step 3 — SSH smoke test

Read host/port from `experiments/.vastai-instance.json`. Then:

```bash
ssh -p <port> -o StrictHostKeyChecking=accept-new root@<host> 'nvidia-smi --query-gpu=name,driver_version --format=csv,noheader'
```

✅ **Verify:** output names a GPU. If `Permission denied (publickey)`, run:

```bash
vastai attach ssh <id> "$(cat ~/.ssh/id_ed25519.pub)"
```

…then retry once. If it still fails, **stop and ask the user** which SSH key they want to use.

### Step 4 — Push the training script

```bash
scp -P <port> examples/quickstart/train.py root@<host>:/workspace/train.py
ssh -p <port> root@<host> 'ls -la /workspace/train.py'
```

✅ **Verify:** `ls` shows non-zero size.

### Step 5 — Launch detached

```bash
ssh -p <port> root@<host> << 'EOF'
cd /workspace
mkdir -p logs results
nohup python train.py > logs/run.log 2>&1 &
echo $! > logs/run.pid
echo "Started PID: $(cat logs/run.pid)"
EOF
```

Save the returned PID into `experiments/.vastai-instance.json` under `active_job`:

```json
{
  "active_job": {
    "pid": <pid>,
    "log_path": "/workspace/logs/run.log",
    "started_at": "<ISO-8601 UTC>",
    "command": "python train.py",
    "experiment": "quickstart"
  }
}
```

### Step 6 — Poll until done

Poll every 15 seconds, max 10 minutes. Each poll is one SSH call:

```bash
ssh -p <port> root@<host> "kill -0 <pid> 2>/dev/null && echo RUNNING || echo DONE; tail -n 5 /workspace/logs/run.log"
```

Show the user the last log lines on each poll so they can see progress. When the first token is `DONE`, fetch the full log:

```bash
ssh -p <port> root@<host> 'cat /workspace/logs/run.log'
```

✅ **Verify:** the final line matches the pattern `[quickstart] done in <N>s  final_acc=<acc>`. If `acc < 0.95` or the final line is missing, **stop** — training ran but the result is off-spec. Show the user the tail and ask whether to continue.

If the 10-minute timeout hits without `DONE`, stop and ask the user whether to keep waiting or kill the job.

### Step 7 — Rsync results back

```bash
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/results/ examples/quickstart/results/
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/logs/    examples/quickstart/logs/
```

✅ **Verify:**
```bash
test -f examples/quickstart/results/metrics.json && cat examples/quickstart/results/metrics.json
```

Diff against `examples/quickstart/expected/metrics.json` — the `final_acc` and `final_loss` should be in the expected range. Surface the diff to the user.

### Step 8 — Append run-log entry

```bash
echo '{"date":"<UTC date>","experiment":"quickstart","status":"success","notes":"Pipeline canary on Vast.ai instance <id>. final_acc=<acc>, wall=<sec>s, device=<device>. See examples/quickstart/results/metrics.json"}' \
  >> experiments/results/run-log.jsonl
```

Use values pulled from `metrics.json` — never invent numbers.

Clear the `active_job` field from `experiments/.vastai-instance.json` (the job is done; instance is still running until the user terminates).

### Handoff

After step 8, print:

```
✅ Canary passed. The pipeline works end-to-end on this machine.

  device=<device>  final_acc=<acc>  wall=<sec>s  cost=<dph * elapsed>

Next steps (do these yourself):
  1. /experiment   — write the positive finding for memory/findings/
  2. /synthesize   — build a report into outputs/
  3. /vastai terminate — release the GPU (~$<estimate>/hr still running)
```

Compute the cost estimate from `dph` (in `.vastai-instance.json`) × hours-since-`started_at`.

## Failure handling

| Step fails | Action |
|---|---|
| 3 (SSH) | Attempt `vastai attach ssh` once, then stop and ask user |
| 4 (scp) | Stop, show error — usually a typo in host/port |
| 5 (launch) | Stop, surface log; usually missing torch in the image |
| 6 (poll timeout) | Don't kill the job — ask the user; the instance may just be slow |
| 6 (acc < 0.95) | Stop, surface tail of log + metrics; treat as a real failure |
| 7 (rsync) | Retry once, then stop |
| 8 (run-log append) | Should never fail — local file write |

The canary's job is to localize failure, so when something breaks, **stop at that step** rather than pushing forward and conflating multiple failures.

## See also

- [`docs/sample-pipeline.md`](../../docs/sample-pipeline.md) — the human-facing walkthrough this skill automates
- [`/vastai`](vastai.md) — the rental lifecycle this skill depends on
- [`/experiment`](experiment.md) — the lifecycle that consumes the canary result
