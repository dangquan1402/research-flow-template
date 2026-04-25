"""Balanced carry and balanced digit sampling for arithmetic training data."""

import random


def compute_carry_length(a: int, b: int) -> int:
    """Count the number of positions with carry in a + b."""
    carry = 0
    length = 0
    while a > 0 or b > 0:
        s = (a % 10) + (b % 10) + carry
        carry = 1 if s >= 10 else 0
        length += carry
        a //= 10
        b //= 10
    return length


def sample_balanced_carry(max_digits: int) -> tuple[int, int]:
    """Sample two numbers with balanced carry chain length."""
    # Pick a target carry length uniformly
    target_carry = random.randint(0, max_digits)
    # Try to find a pair with that carry length (with fallback)
    for _ in range(100):
        n_digits_a = random.randint(1, max_digits)
        n_digits_b = random.randint(1, max_digits)
        a = random.randint(
            10 ** (n_digits_a - 1) if n_digits_a > 1 else 0, 10**n_digits_a - 1
        )
        b = random.randint(
            10 ** (n_digits_b - 1) if n_digits_b > 1 else 0, 10**n_digits_b - 1
        )
        if compute_carry_length(a, b) == target_carry:
            return a, b
    # Fallback: return whatever we got
    return a, b


def sample_balanced_digits(max_digits: int) -> tuple[int, int]:
    """Sample two numbers with balanced digit count distribution."""
    n_digits_a = random.randint(1, max_digits)
    n_digits_b = random.randint(1, max_digits)
    lo_a = 10 ** (n_digits_a - 1) if n_digits_a > 1 else 0
    lo_b = 10 ** (n_digits_b - 1) if n_digits_b > 1 else 0
    a = random.randint(lo_a, 10**n_digits_a - 1)
    b = random.randint(lo_b, 10**n_digits_b - 1)
    return a, b
