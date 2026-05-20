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

Vast.ai has **no native account-level $/hr or budget cap**. Spending is bounded by three layers, applied together. Every `rent` call enforces #2 and #3; #1 is a one-time account setup the user does on the web.

| Layer | Where | What it caps |
|---|---|---|
| **1. Account balance** | https://cloud.vast.ai/billing/ — **disable autobilling**, keep balance low (e.g., $10) | Total spend, account-wide. The only true ceiling. |
| **2. Contract duration** | `duration<N` filter on `vastai search offers` | Wall-clock per instance — Vast.ai locks the contract end date at rent time and auto-stops the box then. |
| **3. Hourly rate** | `dph<X` filter on `vastai search offers` | $/hr per instance. |

**Worst-case math** with all three: `dph_max × duration_max = $ at risk per rental`. E.g., `$0.40/hr × 4hr = $1.60` even if the user forgets to terminate.

### First-time setup nudge

On the first `rent` of a session (or if `experiments/.vastai-history.jsonl` doesn't exist yet), remind the user:

> Before we rent: open https://cloud.vast.ai/billing/ and confirm **autobilling is OFF**. With autobilling on, your card auto-tops-up the balance — there's no spending ceiling. With it off, your loaded balance is the hard cap.

Don't block on this — it's a nudge, not a check. The user owns their billing settings.

### Required rent-time inputs

Always ask the user for these two before searching offers (defaults shown):
- **Max $/hr (`dph_max`)** — default `0.40` (4090 territory). Higher only if user explicitly wants H100/A100.
- **Max contract hours (`duration_max`)** — default `4`. Picks an offer whose contract end is within this window so a forgotten box auto-terminates.

Surface the resulting worst-case `dph_max × duration_max` in dollars before running the search, so the user sees the ceiling they're agreeing to.

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
   - **Max $/hr (`dph_max`)** — default `0.40`
   - **Max contract hours (`duration_max`)** — default `4` (auto-terminates box at the contract end)

Before searching, show the user the worst-case ceiling:

> Ceiling: `dph_max × duration_max` = $`X.XX` if the box runs the full contract.

If this is the first rental of the session, also surface the autobilling nudge from the [Cost Guardrails](#cost-guardrails) section.

### Step 2: Search offers

Always include both guardrail filters in the search query. `duration` is in hours.

```bash
vastai search offers \
  "reliability>0.95 num_gpus=1 gpu_name=<GPU> inet_down>500 dph<<DPH_MAX> duration<<DURATION_MAX>" \
  --order 'dph_total' --limit 5
```

Concrete example (4090, $0.40/hr cap, 4-hour contract cap):

```bash
vastai search offers \
  'reliability>0.95 num_gpus=1 gpu_name=RTX_4090 inet_down>500 dph<0.40 duration<4' \
  --order 'dph_total' --limit 5
```

Show the top 5 to the user with `dph`, `duration` (contract hours remaining), and `gpu_name` columns visible. They pick an offer ID.

If the search returns 0 offers, **don't quietly widen the filters** — report back to the user that no offer matches their guardrails and ask whether to raise `dph_max` or `duration_max`. Silent relaxation defeats the whole point.

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
    "duration_max_hours": 4,
    "worst_case_usd": 1.60,
    "contract_end_at": "2026-05-20T14:30:00Z"
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
- **Guardrails:** `dph_max`, `duration_max_hours`, time until `contract_end_at`, and `accumulated_cost / worst_case_usd` as a progress fraction. If accumulated cost is >80% of `worst_case_usd`, surface a warning.

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
   - `ssh -i ~/.ssh/quandang13 -p 16538 root@ssh9.vast.ai 'tail -n 50 /workspace/logs/run.log'`
   - `ssh -i ~/.ssh/quandang13 -p 16538 root@ssh9.vast.ai 'nvidia-smi'`
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
If `guardrails.worst_case_usd` was set on the instance, compare:
- `total_cost` vs `worst_case_usd` — should be ≤ ceiling. If exceeded (e.g., contract was extended), flag it loudly: "Cost overran guardrail: $X spent vs $Y ceiling — review billing."
- `uptime_hours` vs `duration_max_hours` — same check.

This isn't a hard stop (the box is already destroyed), but it's the feedback signal the user needs to recalibrate guardrails for next time.

---

## Conventions

- **Never commit state files** — `.vastai-instance.json` and `.vastai-history.jsonl` are gitignored
- **One active instance per project** — if `experiments/.vastai-instance.json` exists, ask before renting another
- **Always link to purpose** — every rental should reference an open-question or experiment slug
- **Cost discipline** — show running cost on `status` and `terminate`. Warn if a rental has been running >24h without activity.
- **Cost guardrails are mandatory** — never run `vastai search offers` without `dph<` and `duration<` filters derived from user-stated guardrails. If the search yields nothing, ask the user to raise the cap rather than silently dropping the filter.
- **Prefer Docker over VM** — VMs require SSH keys pre-creation; Docker lets you attach keys after the fact
- **Use `--direct` connections** when available — proxied connections are slower

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` | SSH key not on instance | `vastai attach ssh <id> "$(cat ~/.ssh/id_ed25519.pub)"` |
| `Connection refused` | Instance not ready or wrong port | `vastai show instance <id>` to recheck |
| `No such file: ~/.vast_api_key` | API key not set | `vastai set api-key <KEY>` |
| `Host key verification failed` | Reused port from old rental | `ssh-keygen -R "[host]:port"` then retry |
| `No matching offers` | `dph<` / `duration<` guardrails too tight, or no hosts have a short-enough contract for the chosen GPU | Ask user to raise `dph_max` or `duration_max` — do NOT silently widen the search |

## See Also

- [`/experiment`](experiment.md) — the lifecycle that consumes a rented GPU
- Vast.ai docs: https://docs.vast.ai
