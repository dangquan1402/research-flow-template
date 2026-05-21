"""Tiny char-level transformer baseline on Tiny Shakespeare.

Single-GPU experiment for the research-flow-template. Establishes a baseline
val-loss number that future hypothesis branches can compare against.

Model: 4 layers, 4 heads, 128-dim, context 128. ~0.8M params.
Data:  Tiny Shakespeare (1.1 MB), downloaded on first run.
Steps: 2000 with AdamW + cosine LR.

Outputs (./results/):
  metrics.json    final/best val loss, wall seconds, device, hparams
  loss_curve.csv  step,train_loss,val_loss
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import time
import urllib.request
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).parent
RESULTS = HERE / "results"
DATA = HERE / "data"
RESULTS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

DATA_URL = (
    "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
)
DATA_FILE = DATA / "input.txt"

# hparams
BLOCK = 128
N_LAYER = 4
N_HEAD = 4
N_EMBD = 128
DROPOUT = 0.0
BATCH = 64
STEPS = 2000
LR = 3e-4
WARMUP = 100
EVAL_EVERY = 100
EVAL_BATCHES = 50
SEED = 1337


def load_data() -> tuple[torch.Tensor, torch.Tensor, dict]:
    if not DATA_FILE.exists():
        print(f"[baseline] downloading tiny-shakespeare → {DATA_FILE}")
        urllib.request.urlretrieve(DATA_URL, DATA_FILE)
    text = DATA_FILE.read_text()
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    data = torch.tensor([stoi[c] for c in text], dtype=torch.long)
    n = int(0.9 * len(data))
    return data[:n], data[n:], {"vocab_size": len(chars), "n_chars": len(text)}


def get_batch(data: torch.Tensor, device: str) -> tuple[torch.Tensor, torch.Tensor]:
    ix = torch.randint(len(data) - BLOCK - 1, (BATCH,))
    x = torch.stack([data[i : i + BLOCK] for i in ix])
    y = torch.stack([data[i + 1 : i + 1 + BLOCK] for i in ix])
    return x.to(device), y.to(device)


class CausalSelfAttention(nn.Module):
    def __init__(self):
        super().__init__()
        assert N_EMBD % N_HEAD == 0
        self.qkv = nn.Linear(N_EMBD, 3 * N_EMBD, bias=False)
        self.proj = nn.Linear(N_EMBD, N_EMBD, bias=False)
        self.n_head = N_HEAD
        self.head_dim = N_EMBD // N_HEAD

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, c = x.shape
        q, k, v = self.qkv(x).split(N_EMBD, dim=2)
        q = q.view(b, t, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(b, t, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(b, t, self.n_head, self.head_dim).transpose(1, 2)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        y = y.transpose(1, 2).contiguous().view(b, t, c)
        return self.proj(y)


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(N_EMBD)
        self.attn = CausalSelfAttention()
        self.ln2 = nn.LayerNorm(N_EMBD)
        self.mlp = nn.Sequential(
            nn.Linear(N_EMBD, 4 * N_EMBD),
            nn.GELU(),
            nn.Linear(4 * N_EMBD, N_EMBD),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    def __init__(self, vocab_size: int):
        super().__init__()
        self.tok = nn.Embedding(vocab_size, N_EMBD)
        self.pos = nn.Embedding(BLOCK, N_EMBD)
        self.blocks = nn.ModuleList([Block() for _ in range(N_LAYER)])
        self.ln_f = nn.LayerNorm(N_EMBD)
        self.head = nn.Linear(N_EMBD, vocab_size, bias=False)
        self.head.weight = self.tok.weight  # tied

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok(idx) + self.pos(pos)
        for blk in self.blocks:
            x = blk(x)
        logits = self.head(self.ln_f(x))
        if targets is None:
            return logits, None
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss


@torch.no_grad()
def eval_loss(model: TinyGPT, data: torch.Tensor, device: str) -> float:
    model.eval()
    losses = []
    for _ in range(EVAL_BATCHES):
        x, y = get_batch(data, device)
        _, loss = model(x, y)
        losses.append(loss.item())
    model.train()
    return sum(losses) / len(losses)


def lr_at(step: int) -> float:
    if step < WARMUP:
        return LR * (step + 1) / WARMUP
    progress = (step - WARMUP) / max(1, STEPS - WARMUP)
    return LR * 0.5 * (1 + math.cos(math.pi * progress))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="Wall-clock cap. Exits cleanly after this many seconds even if STEPS not reached.",
    )
    args = parser.parse_args()

    torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[baseline] device={device} torch={torch.__version__} host={platform.node()}")
    if args.max_seconds is not None:
        print(f"[baseline] wall-clock cap: --max-seconds={args.max_seconds}")

    train_data, val_data, meta = load_data()
    print(f"[baseline] vocab={meta['vocab_size']} chars={meta['n_chars']}")

    model = TinyGPT(meta["vocab_size"]).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[baseline] params={n_params:,}")

    opt = torch.optim.AdamW(model.parameters(), lr=LR, betas=(0.9, 0.95))
    curve = RESULTS / "loss_curve.csv"
    curve.write_text("step,train_loss,val_loss\n")

    best_val = float("inf")
    val = float("inf")
    t0 = time.time()
    last_train_loss = float("nan")
    for step in range(STEPS):
        for g in opt.param_groups:
            g["lr"] = lr_at(step)
        x, y = get_batch(train_data, device)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        last_train_loss = loss.item()

        if (step + 1) % EVAL_EVERY == 0 or step == STEPS - 1:
            val = eval_loss(model, val_data, device)
            best_val = min(best_val, val)
            print(
                f"[baseline] step={step + 1}/{STEPS} "
                f"train_loss={last_train_loss:.4f} val_loss={val:.4f} "
                f"lr={opt.param_groups[0]['lr']:.5f}"
            )
            with curve.open("a") as f:
                f.write(f"{step + 1},{last_train_loss:.6f},{val:.6f}\n")

        if args.max_seconds is not None and (time.time() - t0) >= args.max_seconds:
            print(
                f"[baseline] --max-seconds={args.max_seconds} reached at step={step + 1}; "
                "exiting cleanly"
            )
            break

    wall = time.time() - t0
    metrics = {
        "final_val_loss": round(val, 4),
        "best_val_loss": round(best_val, 4),
        "final_train_loss": round(last_train_loss, 4),
        "wall_seconds": round(wall, 2),
        "device": device,
        "torch_version": torch.__version__,
        "host": platform.node(),
        "params": n_params,
        "hparams": {
            "block": BLOCK,
            "n_layer": N_LAYER,
            "n_head": N_HEAD,
            "n_embd": N_EMBD,
            "batch": BATCH,
            "steps": STEPS,
            "lr": LR,
            "warmup": WARMUP,
            "seed": SEED,
        },
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(
        f"[baseline] done in {wall:.1f}s  "
        f"best_val={best_val:.4f}  final_val={val:.4f}  → results/metrics.json"
    )


if __name__ == "__main__":
    main()
