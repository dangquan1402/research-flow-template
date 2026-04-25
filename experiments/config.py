"""Hyperparameter configuration for arithmetic transformer experiments."""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Train arithmetic transformer")
    # Task
    parser.add_argument(
        "--op", choices=["add", "sub", "mul", "mixed"], default="add", help="Operation"
    )
    parser.add_argument("--max_digits", type=int, default=5, help="Max operand digits")
    parser.add_argument(
        "--tokenizer",
        choices=["reversed", "plain"],
        default="reversed",
        help="Output format: reversed (LSB-first) or plain (MSB-first)",
    )
    parser.add_argument(
        "--balanced_carry", type=bool, default=True, help="Use balanced carry sampling"
    )
    parser.add_argument(
        "--scratchpad",
        action="store_true",
        default=False,
        help="Enable scratchpad (intermediate steps) for multiplication",
    )
    parser.add_argument(
        "--pos_encoding",
        choices=["learned", "position_coupling"],
        default="learned",
        help="Positional encoding: learned (standard APE) or position_coupling (Cho 2024)",
    )
    parser.add_argument(
        "--eval_max_digits",
        type=int,
        default=None,
        help="Max digits for OOD evaluation (default: same as max_digits, no OOD eval)",
    )

    # Architecture
    parser.add_argument(
        "--architecture",
        choices=["decoder_only", "looped", "encoder_decoder"],
        default="decoder_only",
        help="Model architecture",
    )
    parser.add_argument("--n_layers", type=int, default=4, help="Number of transformer layers")
    parser.add_argument("--n_heads", type=int, default=4, help="Number of attention heads")
    parser.add_argument("--dim", "--d_model", type=int, default=256, help="Embedding dimension")
    parser.add_argument("--ff_dim", type=int, default=1024, help="FFN hidden dimension")
    parser.add_argument(
        "--activation",
        choices=["gelu", "swiglu", "relu_squared"],
        default="gelu",
        help="Activation function",
    )
    parser.add_argument(
        "--looped", action="store_true", default=False, help="Use looped transformer"
    )
    parser.add_argument("--n_loops", type=int, default=4, help="Number of loops (if looped)")

    # Training
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=256, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--weight_decay", type=float, default=0.5, help="Weight decay")
    parser.add_argument("--warmup_steps", type=int, default=100, help="LR warmup steps")
    parser.add_argument("--train_samples", type=int, default=50000, help="Training samples")
    parser.add_argument("--test_samples", type=int, default=2000, help="Test samples")
    parser.add_argument("--eval_every", type=int, default=5, help="Evaluate every N epochs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    # Checkpointing
    parser.add_argument(
        "--save_checkpoint",
        type=str,
        default=None,
        help="Path to save model checkpoint",
    )
    parser.add_argument(
        "--load_checkpoint",
        type=str,
        default=None,
        help="Path to load model checkpoint",
    )

    # Output
    parser.add_argument(
        "--output_dir",
        type=str,
        default="experiments/results",
        help="Results directory",
    )
    parser.add_argument("--tag", type=str, default="", help="Experiment tag for filename")

    # MLflow tracking
    parser.add_argument(
        "--mlflow", action="store_true", default=False, help="Enable MLflow tracking"
    )
    parser.add_argument(
        "--mlflow_experiment",
        type=str,
        default=None,
        help="MLflow experiment name (default: auto-generated from op/digits)",
    )
    parser.add_argument(
        "--mlflow_tracking_uri",
        type=str,
        default="file:./mlruns",
        help="MLflow tracking URI",
    )

    args = parser.parse_args()

    # Map architecture flag to looped flag for backward compat
    if args.architecture == "looped":
        args.looped = True

    return args
