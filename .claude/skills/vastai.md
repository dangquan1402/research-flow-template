---
name: vastai
description: Rent and manage Vast.ai GPU instances for experiments. Handles setup (API key, SSH key), rent/status/ssh/jupyter/sync/terminate. Tracks state per-project.
user_invocable: true
---

# /vastai — GPU Rental on Vast.ai

This skill manages the full lifecycle of GPU instances rented from Vast.ai for research experiments. It tracks one active instance per project in `experiments/.vastai-instance.json` (gitignored).

## Setup Check (always run first)

Before any subcommand, verify the user's environment. Run these checks in order — stop and resolve the first failure before continuing.

### 1. `vastai` CLI installed?
```bash
which vastai
```
If missing: `uv add vastai` (or `pip install vastai`). Ask user to install before continuing.

### 2. API key configured?
```bash
test -f ~/.vast_api_key && echo "set" || echo "missing"
```
If missing:
1. Tell the user to visit https://cloud.vast.ai/account/ and copy their API key
2. Have them run: `vastai set api-key <KEY>` — this writes `~/.vast_api_key`
3. Do NOT save the key in the repo

### 3. SSH key registered with Vast.ai account?
```bash
vastai show ssh-keys
```
If no keys listed, two options:
- **A — Generate new key:** `vastai create ssh-key` (creates `~/.ssh/id_ed25519` and uploads it)
- **B — Use existing key:** copy `~/.ssh/<your-key>.pub` content and either:
  - Paste at https://cloud.vast.ai/manage-keys/ (UI)
  - Or: `vastai create ssh-key --ssh-key "$(cat ~/.ssh/your-key.pub)"`

**Important:** Account-level keys only apply to instances created *after* the key is added. For existing instances, use `vastai attach ssh <instance_id> <ssh_key>`.

### 4. Resolve the local private key path

The registered Vast.ai pubkey may not match the SSH default (`~/.ssh/id_ed25519` / `~/.ssh/id_rsa`). If it doesn't, every `ssh`/`scp`/`rsync` call needs an explicit `-i <path>` or auth will silently fail with `Permission denied (publickey)`.

To resolve it once, match the registered pubkey content against local `~/.ssh/*.pub`:

```bash
# Get the registered pubkey content (strip "ssh-... ... <comment>" → middle field is the actual key material)
remote_key=$(vastai show ssh-keys --raw 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['public_key'].split()[1])")

# Find local .pub whose middle field matches
for f in ~/.ssh/*.pub; do
  awk -v rk="$remote_key" '$2 == rk { sub(/\.pub$/, "", FILENAME); print FILENAME; exit }' "$f"
done
```

The result is the **private key path** to embed in `experiments/.vastai-instance.json` as `ssh_key`. If multiple Vast.ai keys are registered, ask the user which one to use.

If no local key matches: the user has the registered pubkey somewhere else (different machine, password manager). Ask them to point at the private key path, or generate a new one with `vastai create ssh-key` and rerun.

---

## Cost Guardrails

Vast.ai has **no native account-level $/hr or budget cap, and no per-instance scheduled auto-stop** (`vastai create instance` has no `--end-date` flag). Real cost bounding is therefore a layered defense — server-side where possible, script-side as backup, discipline as the last line.

| Layer | Where it's enforced | What it actually caps |
|---|---|---|
| **1. Account balance + autobilling OFF** | https://cloud.vast.ai/billing/ — disable autobilling, keep balance low (e.g., $10) | Total spend across the whole account. **This is the only true server-side ceiling.** |
| **2. `dph<X` filter** | `vastai search offers` query | $/hr per instance, enforced at search time. |
| **3. `--max-seconds` in training script** | The script itself (e.g., `train.py --max-seconds 600`) | Wall-clock per *run*. Belt-and-suspenders even if the box stays up. |
| **4. Disciplined `/vastai terminate`** | Manual / agent action right after the run finishes | Final close-out. |

### What does NOT work as a guardrail

Documenting these explicitly so the skill doesn't drift back into wishful thinking:

- **`duration<N` search filter** — Vast.ai's `duration` field is "**max rental days available** from the host," not a wall-clock cap on *your* rental. Bigger value = more time available. `duration<0.25` ("offers where host only rents for ≤6 hours") technically narrows the pool, but such offers rarely exist and the host can extend mid-rental. Treat as **advisory only**, not as a wall-clock ceiling.
- **`vastai create instance --end-date`** — does not exist as of this writing. There is no native scheduled auto-stop at creation.
- **Local `at` / `cron` calling `vastai destroy`** — brittle (laptop sleep, network drop). Possible but don't lean on it.

### First-time setup nudge

On the first `rent` of a session (or if `experiments/.vastai-history.jsonl` doesn't exist yet), remind the user:

> Before we rent: open https://cloud.vast.ai/billing/ and confirm **autobilling is OFF**. With autobilling on, your card auto-tops-up the balance — there's no spending ceiling. With it off, your loaded balance is the hard cap.

Don't block on this — it's a nudge, not a check. The user owns their billing settings.

### Required rent-time inputs

Ask the user for these before searching offers (defaults shown):
- **Max $/hr (`dph_max`)** — default `0.40` (4090 territory). Higher only if user explicitly wants H100/A100. Enforced via `dph<` in the search.

  **Gotcha:** the `dph<` filter matches against `dph_base` (the GPU rate), but actual billing is `dph_total` = `dph_base + storage + bandwidth`. A `dph<0.40` filter can surface an offer that costs $0.40+/hr after fees. **Always set the filter ~10% below the user's stated cap** (e.g., user says `$0.40` → use `dph<0.36`), and verify `dph_total` of the picked offer is still under the user's number before creating.
- **Expected runtime in minutes (`runtime_minutes`)** — default `30`. Used for two things:
  - Projecting expected cost (`dph_picked × runtime_minutes / 60`) before launch.
  - Setting a `--max-seconds` value (`runtime_minutes × 60 × 2`, i.e., 2× safety margin) for the training script. The script must accept `--max-seconds`; if it doesn't, surface that as a guardrail gap.

Worst-case bound the user is agreeing to: `dph_max × (max_seconds / 3600)` in dollars, **assuming the user actually terminates promptly when the script exits**. If they don't, the only cap is the account balance (Layer 1).

---

## Subcommand: `rent`

Rent a GPU instance for an experiment.

### Step 1: Ask the user

1. **GPU type** — H100, A100, RTX 4090, etc.
2. **Disk size** — default 30 GB
3. **Docker image** — default `pytorch/pytorch:latest`. Common alternatives:
   - `pytorch/pytorch:latest` — PyTorch with CUDA
   - `nvcr.io/nvidia/pytorch:24.10-py3` — NVIDIA's optimized PyTorch
   - `tensorflow/tensorflow:latest-gpu-jupyter` — TF + built-in Jupyter
4. **Need Jupyter?** If yes, pick an image with `-jupyter` suffix or install in onstart
5. **Expected runtime** — for cost estimation
6. **Cost guardrails** (see [Cost Guardrails](#cost-guardrails) section above):
   - **Max $/hr (`dph_max`)** — default `0.40`. Enforced via `dph<` in the offer search.
   - **Expected runtime (`runtime_minutes`)** — default `30`. Used for projected-cost math and to set `--max-seconds` on the training script (`runtime_minutes × 60 × 2` for 2× safety margin).

Before searching, show the user the projected cost and the wall-clock cap:

> Projected: `dph_max × runtime_minutes / 60` = $`X.XX` if you train the full expected window at the cap rate.
> Script wall-clock cap: `--max-seconds <runtime_minutes × 120>` (2× margin).
> Hard ceiling above this is your account balance — confirm autobilling is OFF.

If this is the first rental of the session, also surface the autobilling nudge from the [Cost Guardrails](#cost-guardrails) section.

### Step 2: Search offers

Include `dph<` as the cost guardrail. `duration` is *not* a wall-clock cap (see [Cost Guardrails § What does NOT work](#cost-guardrails)) — only include it if you want to filter for shorter-contract hosts as a soft signal, with a value in days.

```bash
vastai search offers \
  "reliability>0.95 num_gpus=1 gpu_name=<GPU> inet_down>500 dph<<DPH_MAX>" \
  --order 'dph_total' --limit 5
```

Concrete example (4090, $0.40/hr cap):

```bash
vastai search offers \
  'reliability>0.95 num_gpus=1 gpu_name=RTX_4090 inet_down>500 dph<0.40' \
  --order 'dph_total' --limit 5
```

Show the top 5 to the user with `dph`, `gpu_name`, country (`geolocation`), and reliability visible. They pick an offer ID.

If the search returns 0 offers, **don't quietly widen the filter** — report back and ask whether to raise `dph_max`. Silent relaxation defeats the whole point.

### Step 3: Create instance

```bash
vastai create instance <OFFER_ID> \
  --image pytorch/pytorch:latest \
  --disk 30 \
  --ssh \
  --jupyter \
  --jupyter-lab \
  --direct \
  --onstart-cmd "touch /root/.no_auto_tmux && mkdir -p /workspace/logs"
```

Key flags:
- `--ssh` — enable SSH access (uses account-level keys)
- `--jupyter --jupyter-lab` — start Jupyter Lab on the instance
- `--direct` — direct connection (faster than proxied)
- `--onstart-cmd` — **always include `touch /root/.no_auto_tmux`** so the agent's SSH calls don't get hijacked into a tmux session. Add other bootstrap (e.g., `pip install -r requirements.txt`) after the `&&`.

### Step 4: Wait for instance ready

Poll with `vastai show instances` until the new instance shows `status: running` (usually 30s–2min). Display progress.

### Step 5: Save state

Write to `experiments/.vastai-instance.json`:
```json
{
  "id": 12345678,
  "gpu_name": "H100",
  "image": "pytorch/pytorch:latest",
  "ssh_host": "ssh4.vast.ai",
  "ssh_port": 12345,
  "ssh_key": "~/.ssh/id_ed25519",
  "jupyter_url": "https://...",
  "dph": 1.85,
  "started_at": "2026-05-20T10:30:00Z",
  "purpose": "experiment slug or open-question slug",
  "guardrails": {
    "dph_max": 0.40,
    "runtime_minutes": 30,
    "max_seconds_arg": 3600,
    "projected_usd": 0.20,
    "note": "Wall-clock cap is enforced by the training script's --max-seconds flag, not Vast.ai. Account balance + autobilling-off is the true ceiling."
  }
}
```

The `ssh_key` field is the local private-key path (resolved in setup step 4). All subsequent ssh/scp/rsync calls in this skill **must** include `-i <ssh_key>` (or omit if the registered key matches the SSH default). Read it back with:

```bash
SSH_KEY=$(jq -r '.ssh_key // ""' experiments/.vastai-instance.json | sed "s|^~|$HOME|")
SSH_ARGS="${SSH_KEY:+-i $SSH_KEY}"
# then: ssh $SSH_ARGS -p $port root@$host '...'
```

### Step 6: Print connection info

Show:
- SSH command: `ssh -i <ssh_key> -p <port> root@<host>` (include `-i` only if `ssh_key` differs from SSH defaults)
- Jupyter URL (from `vastai show instance <id>`)
- Hourly cost
- A warning: instance is running and billing has started — destroy with `/vastai terminate` when done

### Step 7: Log to memory

Append to `memory/log.md`:
```
## [YYYY-MM-DD] vastai | rented <gpu> for <purpose>
- Instance: <id> @ $<dph>/hr
- Purpose: <slug>
```

---

## Subcommand: `status`

Show all running instances + the active one for this project.

```bash
vastai show instances
```

If `experiments/.vastai-instance.json` exists, highlight that one. Show:
- Instance ID, GPU, image, hourly cost
- Uptime and accumulated cost
- SSH host/port and Jupyter URL
- **Guardrails:** `dph_max`, projected vs accumulated cost, and `(actual_dph / dph_max)` ratio. If accumulated cost exceeds `projected_usd × 3`, surface a "well over expected runtime — check if you forgot to terminate" warning.

---

## Subcommand: `ssh`

Run a one-shot remote command on the active instance (agent-driven, non-interactive). For interactive use by the human, just print the SSH command.

1. Read `experiments/.vastai-instance.json` — pull `ssh_host`, `ssh_port`, and `ssh_key` (private-key path, may be null/missing → use SSH default keys)
2. **For agent-driven calls** — execute the command and return output:
   ```bash
   ssh -i <ssh_key> -p <ssh_port> root@<ssh_host> '<command>'
   ```
   Omit `-i <ssh_key>` only if the state file has no `ssh_key` field (meaning the registered Vast.ai key matches the SSH default).
   Examples:
   - `ssh -i ~/.ssh/id_ed25519_vastai -p 16538 root@ssh9.vast.ai 'tail -n 50 /workspace/logs/run.log'`
   - `ssh -i ~/.ssh/id_ed25519_vastai -p 16538 root@ssh9.vast.ai 'nvidia-smi'`
3. **For the human** — print the interactive SSH command including `-i` if needed:
   ```bash
   ssh -i <ssh_key> -p <ssh_port> root@<ssh_host>
   ```
4. First connection: silence host-key prompts with `-o StrictHostKeyChecking=accept-new`
5. For Jupyter via SSH tunnel (only if Jupyter URL uses localhost):
   ```bash
   ssh -i <ssh_key> -p <ssh_port> root@<ssh_host> -L 8888:localhost:8888 -N -f
   ```
   (`-N` no remote command, `-f` background)

---

## Subcommand: `jupyter`

Print the Jupyter URL from state. Open in browser if the user wants.

```bash
# Get URL from saved state OR query fresh
vastai show instance <id> | grep jupyter_url
```

---

## Subcommand: `sync`

Move data between local repo and the rented instance.

### Local → Remote (push experiment code)
```bash
scp -i <ssh_key> -P <port> -r experiments/ root@<host>:/workspace/
```

### Remote → Local (pull results)
```bash
scp -i <ssh_key> -P <port> -r root@<host>:/workspace/results/ experiments/results/
```

Or use rsync for incremental syncs:
```bash
rsync -avz -e "ssh -i <ssh_key> -p <port>" experiments/ root@<host>:/workspace/experiments/
rsync -avz -e "ssh -i <ssh_key> -p <port>" root@<host>:/workspace/results/ experiments/results/
```

**Note the uppercase `-P` for scp** (lowercase `-p` for ssh) — Vast.ai gotcha.
Drop `-i <ssh_key>` when the state file's `ssh_key` field is empty/missing.

---

## Workflow: Agent-Driven Training Run

**No tmux, no interactive sessions.** Claude drives the whole loop with non-interactive SSH and SCP — push scripts, launch detached training, poll logs, pull results, terminate. Every command returns to the agent.

> **SSH key reminder:** all `ssh`/`scp`/`rsync` examples below assume the registered Vast.ai key is one of SSH's defaults (`~/.ssh/id_ed25519`, `~/.ssh/id_rsa`). If `experiments/.vastai-instance.json` has an `ssh_key` field set during `rent`, **add `-i <ssh_key>` to every command** (or `-e "ssh -i <ssh_key> -p <port>"` for rsync). The examples omit it for readability — substitute when running.

```
┌─────────────────────────────────────────────────────────────────┐
│  LOCAL (agent)                      REMOTE (Vast.ai)            │
│  ─────────────                      ──────────────              │
│  1. /vastai rent              →     instance running            │
│     (onstart disables tmux)                                     │
│  2. scp -P …  (push code)     →     /workspace/                 │
│  3. ssh "nohup python …  &"   →     training detached, PID saved│
│  4. ssh "tail -n 100 log"   ⇄     poll periodically             │
│  5. scp -P …  (pull results)  ←     /workspace/results/         │
│  6. /vastai terminate                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1: Rent with tmux disabled

When calling `vastai create instance` in the `rent` subcommand, **always include `touch ~/.no_auto_tmux` in `--onstart-cmd`** so SSH connections drop straight to a shell. Example:

```bash
vastai create instance <OFFER_ID> \
  --image pytorch/pytorch:latest \
  --disk 30 --ssh --jupyter --jupyter-lab --direct \
  --onstart-cmd "touch /root/.no_auto_tmux && cd /workspace && echo 'ready'"
```

### Step 2: Push code (scp)

```bash
# Single file
scp -P <port> experiments/train.py root@<host>:/workspace/

# Whole directory, incremental
rsync -avz -e "ssh -p <port>" experiments/ root@<host>:/workspace/experiments/
```

Use the `sync push` subcommand to wrap this — reads host/port from `experiments/.vastai-instance.json`.

### Step 3: Launch training as a detached job

```bash
ssh -p <port> root@<host> << 'EOF'
cd /workspace
mkdir -p logs
nohup python -m experiments.train > logs/run.log 2>&1 &
echo $! > logs/run.pid
echo "Started PID: $(cat logs/run.pid)"
EOF
```

The job runs detached. The SSH command returns immediately with the PID. Save the PID and log path into `experiments/.vastai-instance.json` so subsequent commands know where to look:

```json
{
  "id": 12345678,
  "ssh_host": "ssh4.vast.ai",
  "ssh_port": 12345,
  "active_job": {
    "pid": 8421,
    "log_path": "/workspace/logs/run.log",
    "started_at": "2026-05-20T11:00:00Z",
    "command": "python -m experiments.train"
  }
}
```

### Step 4: Poll status (agent-friendly)

Each poll is a single non-interactive SSH that returns and exits. Agent decides cadence (every 60s, 5min, etc.).

```bash
# Is the process still running?
ssh -p <port> root@<host> "kill -0 <PID> 2>/dev/null && echo RUNNING || echo DONE"

# Latest log
ssh -p <port> root@<host> "tail -n 50 /workspace/logs/run.log"

# GPU usage snapshot
ssh -p <port> root@<host> "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader"

# All three in one call
ssh -p <port> root@<host> "kill -0 <PID> 2>/dev/null && echo RUNNING || echo DONE; tail -n 30 /workspace/logs/run.log; nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader"
```

### Step 5: Pull results

```bash
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/results/ experiments/results/
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/logs/    experiments/results/logs/
```

Append a line to `experiments/results/run-log.jsonl` documenting the run.

### Step 6: Terminate

```bash
/vastai terminate    # offers final sync, then destroys
```

### When the agent needs to read docs / browse the box

Same pattern — one-shot SSH commands:

```bash
# Read a file on the remote
ssh -p <port> root@<host> 'cat /workspace/configs/baseline.yaml'

# List a directory
ssh -p <port> root@<host> 'ls -la /workspace/results/'

# Check disk
ssh -p <port> root@<host> 'df -h /workspace'

# Check what's installed
ssh -p <port> root@<host> 'pip list | grep torch'
```

The agent treats SSH like a remote shell call — each invocation is stateless and returns output immediately.

---

## Subcommand: `terminate`

Destroy the active instance and clean up state.

### Step 1: Confirm with user
Show current instance details + accumulated cost. Ask explicitly: "Destroy instance <id>? (yes/no)"

### Step 2: Pull final results
If the instance has unsaved data in `/workspace/results/`, offer to sync down first:
```bash
rsync -avz -e "ssh -p <port>" root@<host>:/workspace/results/ experiments/results/
```

### Step 3: Destroy
```bash
vastai destroy instance <id>
```

### Step 4: Archive state
Move `experiments/.vastai-instance.json` to `experiments/.vastai-history.jsonl` (append one line) and delete the active file. This keeps a record of past rentals for cost tracking.

### Step 5: Log to memory
```
## [YYYY-MM-DD] vastai | terminated <id> after <hours>h ($<total>)
```

### Step 6: Guardrail post-mortem
If `guardrails.projected_usd` was set on the instance, compare:
- `total_cost` vs `projected_usd` — if `total_cost > 3 × projected_usd`, flag loudly: "Cost ran ~Nx over projection — the box stayed up longer than the expected runtime. Lower `runtime_minutes` next time, or terminate sooner."
- `actual_dph` vs `dph_max` — should always be ≤ (it's enforced by the search). If somehow exceeded (host changed pricing mid-rental? bug?), surface it.

This isn't a hard stop (the box is already destroyed), but it's the feedback signal the user needs to recalibrate guardrails for next time.

---

## Conventions

- **Never commit state files** — `.vastai-instance.json` and `.vastai-history.jsonl` are gitignored
- **One active instance per project** — if `experiments/.vastai-instance.json` exists, ask before renting another
- **Always link to purpose** — every rental should reference an open-question or experiment slug
- **Cost discipline** — show running cost on `status` and `terminate`. Warn if a rental has been running >24h without activity.
- **Cost guardrails are mandatory** — never run `vastai search offers` without a `dph<` filter derived from `dph_max`. If the search yields nothing, ask the user to raise the cap rather than silently dropping the filter. The wall-clock cap belongs in the training script (`--max-seconds`), not the search.
- **Prefer Docker over VM** — VMs require SSH keys pre-creation; Docker lets you attach keys after the fact
- **Use `--direct` connections** when available — proxied connections are slower

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` | SSH key not on instance | `vastai attach ssh <id> "$(cat ~/.ssh/id_ed25519.pub)"` |
| `Connection refused` | Instance not ready or wrong port | `vastai show instance <id>` to recheck |
| `No such file: ~/.vast_api_key` | API key not set | `vastai set api-key <KEY>` |
| `Host key verification failed` | Reused port from old rental | `ssh-keygen -R "[host]:port"` then retry |
| `No matching offers` | `dph<` cap too tight for the chosen GPU | Ask user to raise `dph_max` — do NOT silently widen the search |
| Instance stuck in `actual_status: loading` with `intended_status: stopped` and `status_msg: "Error: Internal error"` | Host accepted the create request but couldn't schedule (resource conflict, container pull failure, host transient issue) | `vastai destroy instance <id>` and try a different offer. Storage charges only — typically ~$0.01. Don't keep retrying the same host. |

## See Also

- [`/experiment`](experiment.md) — the lifecycle that consumes a rented GPU
- Vast.ai docs: https://docs.vast.ai
