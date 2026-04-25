"""Scratchpad multiplication format for intermediate computation steps."""


def generate_scratchpad_mul(a: int, b: int) -> str:
    """Generate scratchpad steps for a * b using aligned reversed partial products.

    Format: partial1|partial2|...|final_answer (all reversed/LSB-first)
    Each partial product = (digit_i of b) * a, shifted by i positions.
    Shift is represented as i leading zeros in the reversed representation.

    Example: 12 * 34 = 408
      4*12=48 (shift 0) reversed: "84"
      3*12=36 (shift 1) → 360 reversed: "063"
      final: 408 reversed: "804"
      Output: "84|063|804"
    """
    b_digits = [int(d) for d in str(b)][::-1]  # LSB-first digits of b
    partial_products = []
    for i, d in enumerate(b_digits):
        pp = d * a  # single-digit * multi-digit
        shifted = pp * (10**i)  # shift by position
        pp_str = str(shifted)[::-1]  # reverse
        # Ensure leading zeros for shift (reversed = trailing zeros become leading)
        # The reversed shifted value naturally has the right zeros
        partial_products.append(pp_str)

    result = a * b
    result_str = str(result)[::-1]
    return "|".join(partial_products) + "|" + result_str
