"""Evaluation functions for arithmetic transformer (MLX)."""

import mlx.core as mx

from ..tokenizer import (
    BOS_ID,
    EOS_ID,
    PAD_ID,
    PC_DIGIT_BASE,
    compute_input_position_ids,
    decode,
    encode,
)


def evaluate_mlx(
    model,
    test_inputs,
    test_answers,
    max_len,
    reverse,
    op,
    scratchpad=False,
    pos_encoding="learned",
):
    """Evaluate model accuracy via greedy autoregressive decoding."""
    correct = 0
    total = 0
    digit_correct = {}
    digit_total = {}
    use_pc = pos_encoding == "position_coupling"

    for inp_str, true_answer in zip(test_inputs, test_answers):
        # Encode input
        ids = [BOS_ID] + encode(inp_str)
        ids_arr = mx.array([ids])

        # Position IDs for position coupling
        if use_pc:
            input_pos = compute_input_position_ids(inp_str)
            n_result_tokens = 0

        # Autoregressive generation
        for _ in range(max_len - len(ids)):
            # Build position IDs
            if use_pc:
                cur_pos = input_pos + [
                    PC_DIGIT_BASE + j for j in range(n_result_tokens)
                ]
                cur_pos_padded = cur_pos + [0] * (max_len - len(cur_pos))
                cur_pos_padded = cur_pos_padded[:max_len]
                pos_arr = mx.array([cur_pos_padded])
            else:
                pos_arr = None

            # Pad to generate
            padded = mx.pad(
                ids_arr,
                [(0, 0), (0, max_len - ids_arr.shape[1])],
                constant_values=PAD_ID,
            )
            logits = model(padded, position_ids=pos_arr)
            next_logit = logits[0, ids_arr.shape[1] - 1]
            next_id = mx.argmax(next_logit).item()

            if next_id == EOS_ID or next_id == PAD_ID:
                break
            ids_arr = mx.concatenate([ids_arr, mx.array([[next_id]])], axis=1)
            if use_pc:
                n_result_tokens += 1

        # Decode prediction
        pred_ids = ids_arr[0, len([BOS_ID] + encode(inp_str)) :].tolist()
        pred_str = decode(pred_ids)

        # For scratchpad, extract final answer (after last |)
        if scratchpad and "|" in pred_str:
            pred_str = pred_str.split("|")[-1]

        # Reverse back if needed (always reversed in scratchpad mode too)
        if reverse or scratchpad:
            pred_str = pred_str[::-1]

        try:
            pred_val = int(pred_str) if pred_str else -1
        except ValueError:
            pred_val = -1

        # Count by digit count of answer
        n_digits = len(str(true_answer))
        digit_total[n_digits] = digit_total.get(n_digits, 0) + 1

        if pred_val == true_answer:
            correct += 1
            digit_correct[n_digits] = digit_correct.get(n_digits, 0) + 1

        total += 1

    accuracy = correct / max(total, 1)
    digit_accuracy = {
        k: digit_correct.get(k, 0) / digit_total[k]
        for k in sorted(digit_total.keys())
    }
    return accuracy, digit_accuracy
