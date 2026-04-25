#!/usr/bin/env python3
"""Entry point for arithmetic transformer training.

Usage:
    python -m experiments.train --op add --max_digits 5
    python -m experiments.train --op mul --max_digits 3 --n_layers 4
    python -m experiments.train --op add --max_digits 5 --architecture looped
    python -m experiments.train --op add --max_digits 5 --pos_encoding position_coupling
"""

from .config import parse_args
from .training.trainer import train_mlx


def main():
    args = parse_args()
    results = train_mlx(args)
    return results


if __name__ == "__main__":
    main()
