"""Data generation for arithmetic training examples."""

import random

from ..tokenizer import OP_MAP
from .sampling import sample_balanced_carry, sample_balanced_digits
from .scratchpad import generate_scratchpad_mul


def generate_example(
    op: str,
    max_digits: int,
    reverse_output: bool = True,
    balanced_carry: bool = True,
    scratchpad: bool = False,
) -> tuple[str, str, int]:
    """Generate one arithmetic example.

    Returns (input_str, full_sequence, answer_int).
    """
    if op == "mixed":
        op = random.choice(["add", "sub", "mul"])

    if balanced_carry and op in ("add", "sub"):
        a, b = sample_balanced_carry(max_digits)
    else:
        a, b = sample_balanced_digits(max_digits)

    if op == "add":
        result = a + b
    elif op == "sub":
        # Ensure a >= b for non-negative results
        if a < b:
            a, b = b, a
        result = a - b
    elif op == "mul":
        # For multiplication, use smaller digit counts
        a = a % (10 ** min(len(str(a)), max_digits))
        b = b % (10 ** min(len(str(b)), max_digits))
        result = a * b
    else:
        raise ValueError(f"Unknown op: {op}")

    op_sym = OP_MAP[op]

    if scratchpad and op == "mul" and a > 0 and b > 0:
        # Scratchpad format: partial products + final answer (all reversed)
        scratch_str = generate_scratchpad_mul(a, b)
        seq = f"{a}{op_sym}{b}={scratch_str}"
    else:
        result_str = str(result)
        if reverse_output:
            result_str = result_str[::-1]
        seq = f"{a}{op_sym}{b}={result_str}"

    input_part = f"{a}{op_sym}{b}="
    return input_part, seq, result


def generate_example_exact_digits(
    op: str, n_digits: int, reverse_output: bool = True
) -> tuple[str, str, int]:
    """Generate one example where both operands have exactly n_digits digits."""
    lo = 10 ** (n_digits - 1) if n_digits > 1 else 0
    hi = 10**n_digits - 1
    a = random.randint(lo, hi)
    b = random.randint(lo, hi)

    if op == "add":
        result = a + b
    elif op == "sub":
        if a < b:
            a, b = b, a
        result = a - b
    elif op == "mul":
        result = a * b
    else:
        raise ValueError(f"Unknown op: {op}")

    op_sym = OP_MAP[op]
    result_str = str(result)
    if reverse_output:
        result_str = result_str[::-1]
    seq = f"{a}{op_sym}{b}={result_str}"
    input_part = f"{a}{op_sym}{b}="
    return input_part, seq, result


def generate_dataset(
    op: str,
    max_digits: int,
    n_samples: int,
    reverse_output: bool = True,
    balanced_carry: bool = True,
    scratchpad: bool = False,
) -> list[tuple[str, str, int]]:
    """Generate a dataset of arithmetic examples."""
    seen = set()
    data = []
    attempts = 0
    while len(data) < n_samples and attempts < n_samples * 10:
        attempts += 1
        inp, seq, ans = generate_example(
            op, max_digits, reverse_output, balanced_carry, scratchpad
        )
        if seq not in seen:
            seen.add(seq)
            data.append((inp, seq, ans))
    return data


def generate_ood_dataset(
    op: str, n_digits: int, n_samples: int, reverse_output: bool = True
) -> list[tuple[str, str, int]]:
    """Generate OOD test examples with exactly n_digits per operand."""
    seen = set()
    data = []
    attempts = 0
    while len(data) < n_samples and attempts < n_samples * 10:
        attempts += 1
        inp, seq, ans = generate_example_exact_digits(op, n_digits, reverse_output)
        if seq not in seen:
            seen.add(seq)
            data.append((inp, seq, ans))
    return data
