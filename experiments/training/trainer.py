"""Training loop for MLX backend."""

import subprocess
import time

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
from loguru import logger
from tqdm import tqdm

from ..data import generate_dataset, generate_ood_dataset
from ..models import get_model
from ..tokenizer import PAD_ID, pad_and_encode, pad_and_encode_with_positions
from .evaluator import evaluate_mlx


def _get_git_commit():
    """Get current git commit hash, or 'unknown' if not in a repo."""
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


def _setup_mlflow(args, n_params, architecture, ff_dim, n_loops, max_len):
    """Initialize MLflow tracking and log params. Returns the active run or None."""
    try:
        import mlflow
    except ImportError:
        logger.warning("mlflow not installed, skipping tracking. pip install mlflow")
        return None

    mlflow.set_tracking_uri(args.mlflow_tracking_uri)

    experiment_name = args.mlflow_experiment or f"{args.op}-{args.max_digits}d"
    mlflow.set_experiment(experiment_name)

    tag = f"-{args.tag}" if args.tag else ""
    run_name = f"{architecture}-{args.n_layers}L{args.n_heads}H{args.dim}D{tag}"

    run = mlflow.start_run(run_name=run_name)

    mlflow.log_params(
        {
            "model.architecture": architecture,
            "model.n_layers": args.n_layers,
            "model.n_heads": args.n_heads,
            "model.dim": args.dim,
            "model.ff_dim": ff_dim,
            "model.activation": args.activation,
            "model.n_loops": n_loops if architecture == "looped" else 0,
            "model.n_params": n_params,
            "model.pos_encoding": args.pos_encoding,
            "model.max_seq_len": max_len,
            "train.lr": args.lr,
            "train.batch_size": args.batch_size,
            "train.epochs": args.epochs,
            "train.weight_decay": args.weight_decay,
            "train.warmup_steps": args.warmup_steps,
            "train.seed": args.seed,
            "data.op": args.op,
            "data.max_digits": args.max_digits,
            "data.tokenizer": args.tokenizer,
            "data.balanced_carry": args.balanced_carry,
            "data.scratchpad": getattr(args, "scratchpad", False),
            "data.train_samples": args.train_samples,
            "data.test_samples": args.test_samples,
        }
    )
    mlflow.set_tags(
        {
            "git_commit": _get_git_commit(),
            "framework": "mlx",
            "architecture": architecture,
        }
    )

    logger.info(f"MLflow tracking: experiment='{experiment_name}', run='{run_name}'")
    return run


def _log_mlflow_metrics(epoch, avg_loss, accuracy, digit_accuracy):
    """Log metrics to MLflow if available."""
    try:
        import mlflow

        mlflow.log_metric("train_loss", avg_loss, step=epoch)
        if accuracy is not None:
            mlflow.log_metric("val_accuracy", accuracy, step=epoch)
            for n_digits, acc in digit_accuracy.items():
                mlflow.log_metric(f"digit_accuracy/{n_digits}d", acc, step=epoch)
    except Exception:
        pass


def _finish_mlflow(run, model, results):
    """Log final artifacts and end the MLflow run."""
    if run is None:
        return
    try:
        import os
        import tempfile

        import mlflow

        # Log best model weights as artifact
        with tempfile.TemporaryDirectory() as tmp:
            weights_path = os.path.join(tmp, "model.safetensors")
            model.save_weights(weights_path)
            mlflow.log_artifact(weights_path, artifact_path="model")

        # Log final summary metrics
        mlflow.log_metric("final_accuracy", results.get("final_accuracy", 0))
        mlflow.log_metric("final_loss", results.get("final_loss", 0))
        mlflow.log_metric("total_time_s", results.get("total_time_s", 0))

        # Log OOD results if present
        for nd, acc in results.get("ood_accuracy", {}).items():
            mlflow.log_metric(f"ood_accuracy/{nd}d", acc)

        mlflow.end_run()
        logger.info("MLflow run completed")
    except Exception as e:
        logger.warning(f"MLflow finalization error: {e}")
        try:
            mlflow.end_run()
        except Exception:
            pass


def count_parameters(model):
    """Count total parameters in MLX model."""
    total = 0
    for k, v in nn.utils.tree_flatten(model.parameters()):
        total += v.size
    return total


def save_checkpoint(model, path):
    """Save model weights to a checkpoint file."""
    model.save_weights(path)
    logger.info(f"Checkpoint saved to {path}")


def load_checkpoint(model, path):
    """Load model weights from a checkpoint file.

    Handles shape mismatches for positional embeddings by copying the
    overlapping portion when the new model has a different sequence length.
    """
    weights = list(mx.load(path).items())

    # Check for pos_emb shape mismatch and handle it
    model_params = dict(nn.utils.tree_flatten(model.parameters()))
    filtered = []
    for key, value in weights:
        if key in model_params and model_params[key].shape != value.shape:
            if "pos_emb" in key:
                # Copy overlapping positions, keep new model's init for the rest
                min_len = min(model_params[key].shape[0], value.shape[0])
                new_weight = model_params[key]
                new_weight = mx.concatenate([value[:min_len], new_weight[min_len:]], axis=0)
                filtered.append((key, new_weight))
                logger.info(f"Resized {key}: {value.shape} -> {new_weight.shape}")
                continue
            else:
                logger.warning(
                    f"Skipping {key}: shape mismatch {value.shape} vs {model_params[key].shape}"
                )
                continue
        filtered.append((key, value))

    model.load_weights(filtered)
    logger.info(f"Checkpoint loaded from {path}")


def train_mlx(args):
    """Training loop for MLX backend."""
    import json
    import os
    import random

    random.seed(args.seed)
    np.random.seed(args.seed)

    # Generate data
    reverse = args.tokenizer == "reversed"
    balanced = args.balanced_carry
    use_scratchpad = args.scratchpad
    use_pc = args.pos_encoding == "position_coupling"

    logger.info(f"Generating {args.train_samples} training examples...")
    if use_scratchpad:
        logger.info("Scratchpad mode enabled for multiplication")
    if use_pc:
        logger.info("Position coupling enabled")
    train_data = generate_dataset(
        args.op,
        args.max_digits,
        args.train_samples,
        reverse,
        balanced,
        use_scratchpad,
    )
    test_data = generate_dataset(
        args.op,
        args.max_digits,
        args.test_samples,
        reverse,
        balanced,
        use_scratchpad,
    )
    logger.info(f"Generated {len(train_data)} train, {len(test_data)} test examples")

    # Determine max sequence length
    max_len = max(len(seq) for _, seq, _ in train_data + test_data) + 2  # +2 for BOS/EOS
    seq_cap = 128 if use_scratchpad else 64
    max_len = min(max_len, seq_cap)

    # For OOD eval, we need a larger max_len
    eval_max_digits = args.eval_max_digits or args.max_digits
    if eval_max_digits > args.max_digits:
        # Max seq: BOS + digits + op + digits + = + (digits+1) + EOS
        ood_max_len = 2 + eval_max_digits + 1 + eval_max_digits + 1 + (eval_max_digits + 1) + 2
        max_len = max(max_len, ood_max_len)

    # Encode tokens (position IDs are recomputed each epoch for fresh random offsets)
    if use_pc:
        train_seqs, _ = pad_and_encode_with_positions(
            [seq for _, seq, _ in train_data], max_len, training=True
        )
    else:
        train_seqs = pad_and_encode([seq for _, seq, _ in train_data], max_len)
    test_inputs = [inp for inp, _, _ in test_data]
    test_answers = [ans for _, _, ans in test_data]

    train_x = mx.array(np.array(train_seqs, dtype=np.int32))

    # Model
    # For SwiGLU, ff_dim is used directly (user should pass the desired inner dim).
    # SwiGLU uses 3 matrices of size (dim, ff_dim) vs GELU's 2 matrices of (dim, ff_dim).
    # To match GELU param count at ff_dim=1536, use --ff_dim 1024 --activation swiglu.
    ff_dim = args.ff_dim

    use_looped = getattr(args, "looped", False)
    n_loops = getattr(args, "n_loops", 4)

    # Determine architecture
    architecture = getattr(args, "architecture", "decoder_only")
    if use_looped and architecture == "decoder_only":
        architecture = "looped"

    model = get_model(
        architecture,
        n_layers=args.n_layers,
        dim=args.dim,
        n_heads=args.n_heads,
        ff_dim=ff_dim,
        max_seq_len=max_len,
        pos_encoding=args.pos_encoding,
        activation=args.activation,
        n_loops=n_loops,
    )
    mx.eval(model.parameters())

    # Load checkpoint if specified
    if args.load_checkpoint:
        load_checkpoint(model, args.load_checkpoint)

    n_params = count_parameters(model)
    looped_str = f", looped={n_loops}x" if architecture == "looped" else ""
    logger.info(
        f"Model: {args.n_layers}L/{args.n_heads}H/{args.dim}D{looped_str}, {n_params:,} params"
    )

    # MLflow tracking
    use_mlflow = getattr(args, "mlflow", False)
    mlflow_run = None
    if use_mlflow:
        mlflow_run = _setup_mlflow(args, n_params, architecture, ff_dim, n_loops, max_len)

    # Optimizer with cosine schedule
    warmup_steps = args.warmup_steps
    total_steps = args.epochs * (len(train_data) // args.batch_size + 1)

    schedule = optim.cosine_decay(args.lr, total_steps - warmup_steps, end=args.lr * 0.1)
    if warmup_steps > 0:
        schedule = optim.join_schedules(
            [optim.linear_schedule(0, args.lr, warmup_steps), schedule],
            [warmup_steps],
        )
    optimizer = optim.AdamW(
        learning_rate=schedule, weight_decay=args.weight_decay, betas=[0.9, 0.99]
    )

    # Loss function
    def loss_fn(model, x, pos=None):
        pos_input = pos[:, :-1] if pos is not None else None
        targets = x[:, 1:]
        mask = (targets != PAD_ID).astype(mx.float32)

        if architecture == "looped":
            # Progressive loss: compute loss at each loop iteration, average
            all_logits = model(x[:, :-1], position_ids=pos_input, return_all_logits=True)
            total_loss = mx.zeros(())
            for logits in all_logits:
                ce = nn.losses.cross_entropy(logits, targets, reduction="none")
                total_loss = total_loss + (ce * mask).sum() / mask.sum()
            return total_loss / len(all_logits)
        else:
            logits = model(x[:, :-1], position_ids=pos_input)
            ce = nn.losses.cross_entropy(logits, targets, reduction="none")
            return (ce * mask).sum() / mask.sum()

    loss_and_grad = nn.value_and_grad(model, loss_fn)

    # Training
    results = {
        "framework": "mlx",
        "op": args.op,
        "max_digits": args.max_digits,
        "pos_encoding": args.pos_encoding,
        "tokenizer": args.tokenizer,
        "balanced_carry": args.balanced_carry,
        "scratchpad": use_scratchpad,
        "max_seq_len": max_len,
        "architecture": architecture,
        "n_layers": args.n_layers,
        "n_heads": args.n_heads,
        "dim": args.dim,
        "ff_dim": ff_dim,
        "activation": args.activation,
        "looped": architecture == "looped",
        "n_loops": n_loops if architecture == "looped" else None,
        "n_params": n_params,
        "train_samples": len(train_data),
        "test_samples": len(test_data),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "weight_decay": args.weight_decay,
        "seed": args.seed,
        "epoch_logs": [],
    }

    logger.info(f"Training for {args.epochs} epochs, batch_size={args.batch_size}")

    global_step = 0
    n_total_batches = len(train_data) // args.batch_size + 1
    start_time = time.time()

    epoch_bar = tqdm(range(1, args.epochs + 1), desc="Epochs", unit="ep")
    for epoch in epoch_bar:
        epoch_start = time.time()

        # Shuffle
        perm = np.random.permutation(len(train_data))
        train_x_shuffled = train_x[mx.array(perm)]

        # For position coupling, re-compute position IDs each epoch
        # (different random offsets per epoch)
        if use_pc:
            _, new_pos = pad_and_encode_with_positions(
                [seq for _, seq, _ in train_data], max_len, training=True
            )
            train_p_shuffled = mx.array(np.array(new_pos, dtype=np.int32))[mx.array(perm)]
        else:
            train_p_shuffled = None

        epoch_loss = 0.0
        n_batches = 0

        batch_iter = range(0, len(train_data), args.batch_size)
        batch_bar = tqdm(
            batch_iter,
            desc=f"Epoch {epoch}",
            leave=False,
            unit="batch",
            total=n_total_batches,
        )
        for i in batch_bar:
            batch = train_x_shuffled[i : i + args.batch_size]
            if batch.shape[0] == 0:
                continue

            batch_pos = (
                train_p_shuffled[i : i + args.batch_size] if train_p_shuffled is not None else None
            )

            loss, grads = loss_and_grad(model, batch, batch_pos)
            optimizer.update(model, grads)
            mx.eval(model.parameters(), optimizer.state)

            epoch_loss += loss.item()
            n_batches += 1
            global_step += 1
            batch_bar.set_postfix(loss=f"{epoch_loss / n_batches:.4f}")

        avg_loss = epoch_loss / max(n_batches, 1)
        epoch_time = time.time() - epoch_start

        # Evaluate every eval_every epochs
        accuracy = None
        digit_accuracy = {}
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            accuracy, digit_accuracy = evaluate_mlx(
                model,
                test_inputs,
                test_answers,
                max_len,
                reverse,
                args.op,
                use_scratchpad,
                pos_encoding=args.pos_encoding,
            )

        log = {
            "epoch": epoch,
            "loss": round(avg_loss, 4),
            "time_s": round(epoch_time, 2),
        }
        if accuracy is not None:
            log["accuracy"] = round(accuracy, 4)
            log["digit_accuracy"] = digit_accuracy

        results["epoch_logs"].append(log)

        # MLflow per-epoch metrics
        if use_mlflow:
            _log_mlflow_metrics(epoch, avg_loss, accuracy, digit_accuracy)

        acc_str = f"  acc={accuracy:.2%}" if accuracy is not None else ""
        digit_str = ""
        if digit_accuracy:
            digit_str = "  " + " ".join(f"{k}d:{v:.0%}" for k, v in sorted(digit_accuracy.items()))
        epoch_bar.set_postfix_str(f"loss={avg_loss:.4f}{acc_str}")
        logger.info(
            f"Epoch {epoch:3d} | loss={avg_loss:.4f} | {epoch_time:.1f}s{acc_str}{digit_str}"
        )

        # Incremental save after each eval epoch (crash-safe)
        if accuracy is not None:
            os.makedirs(args.output_dir, exist_ok=True)
            tag = f"_{args.tag}" if args.tag else ""
            pos_tag = f"_{args.pos_encoding}" if args.pos_encoding != "learned" else ""
            partial_fname = (
                f"{args.op}_{args.max_digits}d_{args.tokenizer}"
                f"_{args.n_layers}L{args.n_heads}H{args.dim}D"
                f"{pos_tag}{tag}.partial.json"
            )
            partial_path = os.path.join(args.output_dir, partial_fname)
            partial_results = dict(results)
            partial_results["total_time_s"] = round(time.time() - start_time, 2)
            partial_results["final_accuracy"] = accuracy
            partial_results["final_loss"] = avg_loss
            partial_results["status"] = "in_progress"
            partial_results["completed_epochs"] = epoch
            with open(partial_path, "w") as f:
                json.dump(partial_results, f, indent=2)
            logger.debug(f"Partial results saved to {partial_path}")

    total_time = time.time() - start_time
    results["total_time_s"] = round(total_time, 2)
    results["final_accuracy"] = results["epoch_logs"][-1].get("accuracy", 0)
    results["final_loss"] = results["epoch_logs"][-1]["loss"]

    logger.success(f"Done in {total_time:.1f}s. Final accuracy: {results['final_accuracy']:.2%}")

    # Save checkpoint if specified
    if args.save_checkpoint:
        save_checkpoint(model, args.save_checkpoint)

    # OOD evaluation
    if eval_max_digits > args.max_digits:
        logger.info(f"OOD Length Generalization Evaluation (train max_digits={args.max_digits})")
        ood_results = {}
        for nd in tqdm(range(1, eval_max_digits + 1), desc="OOD eval", unit="digits"):
            ood_data = generate_ood_dataset(args.op, nd, 500, reverse)
            ood_inputs = [inp for inp, _, _ in ood_data]
            ood_answers = [ans for _, _, ans in ood_data]
            acc, _ = evaluate_mlx(
                model,
                ood_inputs,
                ood_answers,
                max_len,
                reverse,
                args.op,
                False,
                pos_encoding=args.pos_encoding,
            )
            ood_results[nd] = round(acc, 4)
            in_dist = "ID" if nd <= args.max_digits else "OOD"
            logger.info(f"  {nd:2d}-digit ({in_dist}): {acc:.2%}")
        results["ood_accuracy"] = ood_results

    # MLflow: log final artifacts and end run
    if use_mlflow:
        _finish_mlflow(mlflow_run, model, results)

    # Save final results
    os.makedirs(args.output_dir, exist_ok=True)
    tag = f"_{args.tag}" if args.tag else ""
    pos_tag = f"_{args.pos_encoding}" if args.pos_encoding != "learned" else ""
    fname = (
        f"{args.op}_{args.max_digits}d_{args.tokenizer}"
        f"_{args.n_layers}L{args.n_heads}H{args.dim}D"
        f"{pos_tag}{tag}.json"
    )
    out_path = os.path.join(args.output_dir, fname)
    results["status"] = "complete"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {out_path}")

    # Clean up partial results file
    partial_fname = fname.replace(".json", ".partial.json")
    partial_path = os.path.join(args.output_dir, partial_fname)
    if os.path.exists(partial_path):
        os.remove(partial_path)
        logger.debug(f"Cleaned up {partial_path}")

    return results
