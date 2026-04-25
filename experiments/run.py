#!/usr/bin/env python3
"""Run experiments from YAML configs.

Usage:
    uv run python -m experiments.run experiments/configs/baselines/add-5d-reversed-2L384D.yaml
    uv run python -m experiments.run experiments/configs/sweeps/depth-vs-width.yaml
    uv run python -m experiments.run experiments/configs/baselines/*.yaml  # batch
"""

import argparse
import json
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from .config_loader import is_sweep_config, load_experiment_config, load_sweep_config
from .training.trainer import train_mlx

RUN_LOG_PATH = Path("experiments/results/run-log.jsonl")


def _get_git_commit():
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .strip()
            .decode()
        )
    except Exception:
        return "unknown"


def _append_run_log(entry: dict):
    """Append a single entry to run-log.jsonl."""
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _classify_error(e: Exception) -> str:
    """Classify an exception into a failure category."""
    msg = str(e).lower()
    if "out of memory" in msg or "oom" in msg or "memory" in msg:
        return "failed:infra"
    if "shape" in msg or "dimension" in msg or "mismatch" in msg:
        return "failed:config"
    if "file not found" in msg or "no such file" in msg:
        return "failed:config"
    return "failed:bug"


def run_single(args, config_path: str, run_name: str) -> dict:
    """Run a single experiment and return the run log entry."""
    meta = getattr(args, "_meta", {})
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config_path,
        "run_name": run_name,
        "question": meta.get("question", ""),
        "hypothesis": meta.get("hypothesis", ""),
        "acceptance_criteria": meta.get("acceptance_criteria", ""),
        "git_commit": _get_git_commit(),
    }

    try:
        logger.info(f"=== Running: {run_name} ({config_path}) ===")
        results = train_mlx(args)

        entry["status"] = "success"
        entry["final_accuracy"] = results.get("final_accuracy", 0)
        entry["final_loss"] = results.get("final_loss", 0)
        entry["time_s"] = results.get("total_time_s", 0)
        entry["n_params"] = results.get("n_params", 0)
        entry["result_file"] = _find_result_file(args)

        # Check acceptance criteria (simple numeric check)
        criteria = meta.get("acceptance_criteria", "")
        if criteria and entry["final_accuracy"] is not None:
            entry["meets_criteria"] = _check_criteria(criteria, entry["final_accuracy"])

        logger.success(f"Completed: {run_name} — accuracy={entry['final_accuracy']:.2%}")

    except KeyboardInterrupt:
        entry["status"] = "failed:infra"
        entry["error_type"] = "KeyboardInterrupt"
        entry["error_message"] = "Interrupted by user"
        logger.warning(f"Interrupted: {run_name}")
        raise
    except Exception as e:
        entry["status"] = _classify_error(e)
        entry["error_type"] = type(e).__name__
        entry["error_message"] = str(e)[:500]
        logger.error(f"Failed: {run_name} — {entry['status']}: {e}")
        traceback.print_exc()

    _append_run_log(entry)
    return entry


def _find_result_file(args) -> str:
    """Reconstruct the result filename from args (matches trainer logic)."""
    tag = f"_{args.tag}" if args.tag else ""
    pos_tag = f"_{args.pos_encoding}" if args.pos_encoding != "learned" else ""
    return (
        f"{args.op}_{args.max_digits}d_{args.tokenizer}"
        f"_{args.n_layers}L{args.n_heads}H{args.dim}D"
        f"{pos_tag}{tag}.json"
    )


def _check_criteria(criteria: str, accuracy: float) -> bool:
    """Simple acceptance criteria check. Supports '>X%' format."""
    criteria = criteria.strip()
    if criteria.startswith(">"):
        try:
            threshold = float(criteria[1:].strip().rstrip("%")) / 100
            return accuracy > threshold
        except ValueError:
            pass
    if criteria.startswith(">="):
        try:
            threshold = float(criteria[2:].strip().rstrip("%")) / 100
            return accuracy >= threshold
        except ValueError:
            pass
    return False  # Can't parse, don't assume


def main():
    parser = argparse.ArgumentParser(description="Run experiments from YAML configs")
    parser.add_argument("configs", nargs="+", help="YAML config file paths")
    parser.add_argument("--dry-run", action="store_true", help="Print configs without running")
    cli_args = parser.parse_args()

    entries = []
    for config_path in cli_args.configs:
        path = Path(config_path)
        if not path.exists():
            logger.error(f"Config not found: {path}")
            continue

        if is_sweep_config(str(path)):
            runs = load_sweep_config(str(path))
            for run_name, args in runs:
                if cli_args.dry_run:
                    logger.info(f"[DRY RUN] {run_name}: {vars(args)}")
                    continue
                entry = run_single(args, str(path), run_name)
                entries.append(entry)
        else:
            args = load_experiment_config(str(path))
            run_name = getattr(args, "_meta", {}).get("name", path.stem)
            if cli_args.dry_run:
                logger.info(f"[DRY RUN] {run_name}: {vars(args)}")
                continue
            entry = run_single(args, str(path), run_name)
            entries.append(entry)

    # Summary
    if entries:
        successes = sum(1 for e in entries if e["status"] == "success")
        failures = len(entries) - successes
        logger.info(f"\n=== Summary: {successes} succeeded, {failures} failed ===")
        for e in entries:
            status = e["status"]
            acc = e.get("final_accuracy")
            acc_str = f" acc={acc:.2%}" if acc is not None else ""
            criteria_str = ""
            if "meets_criteria" in e:
                criteria_str = " [PASS]" if e["meets_criteria"] else " [FAIL]"
            logger.info(f"  {e['run_name']}: {status}{acc_str}{criteria_str}")


if __name__ == "__main__":
    main()
