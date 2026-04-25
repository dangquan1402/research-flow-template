"""Load experiment configs from YAML files.

Converts YAML experiment definitions to argparse.Namespace objects
compatible with train_mlx(). Supports single configs and sweeps.

Usage:
    from experiments.config_loader import load_experiment_config, load_sweep_config

    args = load_experiment_config("experiments/configs/baselines/add-5d.yaml")
    runs = load_sweep_config("experiments/configs/sweeps/depth-vs-width.yaml")
"""

import argparse
from pathlib import Path

import yaml
from loguru import logger

# Default values matching config.py defaults
_DEFAULTS = {
    "op": "add",
    "max_digits": 5,
    "tokenizer": "reversed",
    "balanced_carry": True,
    "scratchpad": False,
    "pos_encoding": "learned",
    "eval_max_digits": None,
    "architecture": "decoder_only",
    "n_layers": 4,
    "n_heads": 4,
    "dim": 256,
    "ff_dim": 1024,
    "activation": "gelu",
    "looped": False,
    "n_loops": 4,
    "epochs": 50,
    "batch_size": 256,
    "lr": 1e-3,
    "weight_decay": 0.5,
    "warmup_steps": 100,
    "train_samples": 50000,
    "test_samples": 2000,
    "eval_every": 5,
    "seed": 42,
    "save_checkpoint": None,
    "load_checkpoint": None,
    "output_dir": "experiments/results",
    "tag": "",
    "mlflow": False,
    "mlflow_experiment": None,
    "mlflow_tracking_uri": "file:./mlruns",
}

# Map from YAML section.key to flat argparse dest name
_SECTION_MAP = {
    "task": [
        "op",
        "max_digits",
        "tokenizer",
        "balanced_carry",
        "scratchpad",
        "pos_encoding",
        "eval_max_digits",
    ],
    "architecture": [
        "architecture",
        "n_layers",
        "n_heads",
        "dim",
        "ff_dim",
        "activation",
        "looped",
        "n_loops",
    ],
    "training": [
        "epochs",
        "batch_size",
        "lr",
        "weight_decay",
        "warmup_steps",
        "train_samples",
        "test_samples",
        "eval_every",
        "seed",
    ],
    "checkpoint": ["save_checkpoint", "load_checkpoint"],
    "output": ["output_dir", "tag"],
    "mlflow": ["mlflow_experiment", "mlflow_tracking_uri"],
}

_VALID_KEYS = set(_DEFAULTS.keys())


def _flatten_config(config: dict) -> dict:
    """Flatten a nested YAML config into a flat dict of argparse dest names."""
    flat = {}

    # Handle mlflow section specially: mlflow.enabled -> mlflow,
    # mlflow.experiment -> mlflow_experiment, mlflow.tracking_uri -> mlflow_tracking_uri
    mlflow_section = config.get("mlflow", {})
    if isinstance(mlflow_section, dict):
        if "enabled" in mlflow_section:
            flat["mlflow"] = mlflow_section["enabled"]
        if "experiment" in mlflow_section:
            flat["mlflow_experiment"] = mlflow_section["experiment"]
        if "tracking_uri" in mlflow_section:
            flat["mlflow_tracking_uri"] = mlflow_section["tracking_uri"]

    for section, keys in _SECTION_MAP.items():
        section_data = config.get(section, {})
        if not isinstance(section_data, dict):
            continue
        for key in keys:
            if key in section_data:
                flat[key] = section_data[key]

    # Warn on unknown keys
    for section_name, section_data in config.items():
        if section_name in ("meta",) or not isinstance(section_data, dict):
            continue
        if section_name not in _SECTION_MAP and section_name != "mlflow":
            logger.warning(f"Unknown config section: {section_name}")
        if isinstance(section_data, dict):
            for key in section_data:
                _mlflow_aliases = {"enabled", "experiment", "tracking_uri"}
                if key not in _VALID_KEYS and key not in _mlflow_aliases:
                    logger.warning(f"Unknown config key: {section_name}.{key}")

    return flat


def _to_namespace(flat: dict, meta: dict | None = None) -> argparse.Namespace:
    """Build a Namespace from flat config dict, filling defaults."""
    merged = dict(_DEFAULTS)
    merged.update(flat)

    # Map architecture to looped flag for backward compat
    if merged.get("architecture") == "looped":
        merged["looped"] = True

    # Attach meta for downstream use
    ns = argparse.Namespace(**merged)
    ns._meta = meta or {}
    return ns


def load_experiment_config(yaml_path: str) -> argparse.Namespace:
    """Load a single experiment YAML config, return Namespace for train_mlx()."""
    path = Path(yaml_path)
    with open(path) as f:
        config = yaml.safe_load(f)

    meta = config.get("meta", {})
    flat = _flatten_config(config)

    # Use meta.name as tag if no tag specified
    if "tag" not in flat and meta.get("name"):
        flat["tag"] = meta["name"]

    logger.info(f"Loaded config: {meta.get('name', path.stem)} from {path}")
    return _to_namespace(flat, meta)


def load_sweep_config(yaml_path: str) -> list[tuple[str, argparse.Namespace]]:
    """Load a sweep YAML config, return list of (run_name, Namespace) pairs."""
    path = Path(yaml_path)
    with open(path) as f:
        config = yaml.safe_load(f)

    meta = config.get("meta", {})
    base = config.get("base", {})
    runs = config.get("runs", [])

    if not runs:
        raise ValueError(f"Sweep config {path} has no 'runs' section")

    base_flat = _flatten_config(base)
    results = []

    for run_def in runs:
        run_name = run_def.pop("name", f"run-{len(results)}")
        # Merge base + run overrides
        run_flat = dict(base_flat)
        for section_data in run_def.values():
            if isinstance(section_data, dict):
                for k, v in section_data.items():
                    if k in _VALID_KEYS:
                        run_flat[k] = v
                    else:
                        logger.warning(f"Unknown sweep key: {k}")
            # Handle flat overrides too
        run_flat["tag"] = run_name
        run_meta = dict(meta)
        run_meta["run_name"] = run_name
        results.append((run_name, _to_namespace(run_flat, run_meta)))

    logger.info(f"Loaded sweep: {meta.get('name', path.stem)} with {len(results)} runs")
    return results


def is_sweep_config(yaml_path: str) -> bool:
    """Check if a YAML config is a sweep (has 'runs' key)."""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    return "runs" in config
