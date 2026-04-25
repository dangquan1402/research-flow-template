"""Vocabulary, encode/decode, and position coupling for arithmetic transformer."""

import random

# Vocab: 0-9, +, -, *, =, <pad>, <eos>, <bos>, | (scratchpad step separator)
TOKENS = list("0123456789+-*=") + ["<pad>", "<eos>", "<bos>", "|"]
TOK2ID = {t: i for i, t in enumerate(TOKENS)}
ID2TOK = {i: t for t, i in TOK2ID.items()}
VOCAB_SIZE = len(TOKENS)
PAD_ID = TOK2ID["<pad>"]
EOS_ID = TOK2ID["<eos>"]
BOS_ID = TOK2ID["<bos>"]
SEP_ID = TOK2ID["|"]
OP_MAP = {"add": "+", "sub": "-", "mul": "*"}


def encode(s: str) -> list[int]:
    return [TOK2ID[c] for c in s]


def decode(ids: list[int]) -> str:
    return "".join(ID2TOK[i] for i in ids if i not in (PAD_ID, EOS_ID, BOS_ID))


# ── Position Coupling ────────────────────────────────────────────────────────

# Position IDs for special tokens (low values, distinct from digit positions)
PC_BOS_POS = 0
PC_OP_POS = 1
PC_EQ_POS = 2
PC_EOS_POS = 3
PC_DIGIT_BASE = 4  # Digit significance s → position ID PC_DIGIT_BASE + s
PC_MAX_POS = 256  # Embedding table size for position coupling


def compute_position_coupling_ids(seq_str, training=True):
    """Compute position IDs for position coupling encoding.

    Digits of equal significance across operands and result share the same
    position ID, so the model learns to align by significance regardless of
    operand length.

    For addition with reversed output (e.g., "123+456=975"):
    - Operand digits are MSB-first: index i in k-digit number → significance k-1-i
    - Result digits are LSB-first (reversed): index j → significance j
    - Special tokens (<bos>, +, =, <eos>) get unique position IDs

    During training, a random offset in [1, 100] is added to all position IDs
    so the model cannot memorize absolute positions.
    """
    op_idx = next(i for i, c in enumerate(seq_str) if c in "+-*")
    eq_idx = seq_str.index("=")

    op1 = seq_str[:op_idx]
    op2 = seq_str[op_idx + 1 : eq_idx]
    result = seq_str[eq_idx + 1 :]

    pos_ids = [PC_BOS_POS]

    # Op1 (MSB-first): digit at index i → significance (len-1-i)
    for i in range(len(op1)):
        pos_ids.append(PC_DIGIT_BASE + len(op1) - 1 - i)

    pos_ids.append(PC_OP_POS)

    # Op2 (MSB-first)
    for i in range(len(op2)):
        pos_ids.append(PC_DIGIT_BASE + len(op2) - 1 - i)

    pos_ids.append(PC_EQ_POS)

    # Result (LSB-first / reversed): digit at index j → significance j
    for j in range(len(result)):
        pos_ids.append(PC_DIGIT_BASE + j)

    pos_ids.append(PC_EOS_POS)

    if training:
        offset = random.randint(1, 100)
        pos_ids = [p + offset for p in pos_ids]

    return pos_ids


def compute_input_position_ids(inp_str):
    """Compute position IDs for input-only string (for autoregressive eval).

    inp_str looks like "123+456=" (includes trailing =).
    Returns position IDs including BOS at the start.
    """
    op_idx = next(i for i, c in enumerate(inp_str) if c in "+-*")
    # eq_idx is the last char
    op1 = inp_str[:op_idx]
    op2 = inp_str[op_idx + 1 : -1]  # exclude trailing '='

    pos_ids = [PC_BOS_POS]

    for i in range(len(op1)):
        pos_ids.append(PC_DIGIT_BASE + len(op1) - 1 - i)

    pos_ids.append(PC_OP_POS)

    for i in range(len(op2)):
        pos_ids.append(PC_DIGIT_BASE + len(op2) - 1 - i)

    pos_ids.append(PC_EQ_POS)

    return pos_ids


def pad_and_encode(sequences: list[str], max_len: int) -> list[list[int]]:
    """Encode and pad sequences to max_len."""
    result = []
    for seq in sequences:
        ids = [BOS_ID] + encode(seq) + [EOS_ID]
        ids = ids[:max_len]
        ids += [PAD_ID] * (max_len - len(ids))
        result.append(ids)
    return result


def pad_and_encode_with_positions(
    sequences: list[str], max_len: int, training: bool = True
) -> tuple[list[list[int]], list[list[int]]]:
    """Encode sequences and compute position coupling IDs, padded to max_len."""
    encoded = []
    positions = []
    for seq in sequences:
        ids = [BOS_ID] + encode(seq) + [EOS_ID]
        pos = compute_position_coupling_ids(seq, training=training)

        ids = ids[:max_len]
        pos = pos[:max_len]

        ids += [PAD_ID] * (max_len - len(ids))
        pos += [0] * (max_len - len(pos))

        encoded.append(ids)
        positions.append(pos)

    return encoded, positions
