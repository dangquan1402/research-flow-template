"""Tiny end-to-end training run for the research-flow quickstart.

Trains a 2-layer MLP on synthetic data for ~30s on any GPU (CPU works too).
Designed to prove the vast.ai rental → SSH → train → sync → report pipeline.

Outputs (written to ./results/, picked up by `rsync` in the walkthrough):
  - metrics.json   final test accuracy + wall time + device
  - loss_curve.csv epoch,loss,acc
  - run.log        stdout log (captured by `nohup ... > run.log`)
"""

from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def make_centers(n_classes: int, dim: int) -> torch.Tensor:
    gc = torch.Generator().manual_seed(42)
    return torch.randn(n_classes, dim, generator=gc) * 3


def make_data(centers: torch.Tensor, n: int, seed: int):
    n_classes, dim = centers.shape
    g = torch.Generator().manual_seed(seed)
    y = torch.randint(0, n_classes, (n,), generator=g)
    x = centers[y] + torch.randn(n, dim, generator=g)
    return x, y


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[quickstart] device={device} torch={torch.__version__} host={platform.node()}")

    dim, n_classes, n_train, n_test, epochs, bs = 64, 10, 20_000, 4_000, 8, 256
    centers = make_centers(n_classes, dim)
    x_tr, y_tr = make_data(centers, n_train, seed=1)
    x_te, y_te = make_data(centers, n_test, seed=2)
    train_loader = DataLoader(TensorDataset(x_tr, y_tr), batch_size=bs, shuffle=True)

    model = nn.Sequential(
        nn.Linear(dim, 128),
        nn.ReLU(),
        nn.Linear(128, 128),
        nn.ReLU(),
        nn.Linear(128, n_classes),
    ).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    curve_path = RESULTS / "loss_curve.csv"
    curve_path.write_text("epoch,loss,acc\n")

    train_loss, acc = float("nan"), float("nan")
    t0 = time.time()
    for epoch in range(epochs):
        model.train()
        running = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            running += loss.item() * xb.size(0)
        train_loss = running / n_train

        model.eval()
        with torch.no_grad():
            preds = model(x_te.to(device)).argmax(1).cpu()
            acc = (preds == y_te).float().mean().item()

        print(f"[quickstart] epoch={epoch + 1}/{epochs} loss={train_loss:.4f} acc={acc:.4f}")
        with curve_path.open("a") as f:
            f.write(f"{epoch + 1},{train_loss:.6f},{acc:.6f}\n")

    wall = time.time() - t0
    metrics = {
        "final_acc": acc,
        "final_loss": train_loss,
        "wall_seconds": round(wall, 2),
        "device": device,
        "torch_version": torch.__version__,
        "host": platform.node(),
        "epochs": epochs,
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"[quickstart] done in {wall:.1f}s  final_acc={acc:.4f}  → results/metrics.json")


if __name__ == "__main__":
    main()
