"""Decoder-only arithmetic transformer (MLX)."""

import mlx.core as mx
import mlx.nn as nn

from ..tokenizer import PC_MAX_POS, VOCAB_SIZE
from . import register_model
from .base import RMSNorm, TransformerBlock


@register_model("decoder_only")
class ArithmeticTransformer(nn.Module):
    def __init__(
        self,
        n_layers: int,
        dim: int,
        n_heads: int,
        ff_dim: int,
        max_seq_len: int,
        pos_encoding: str = "learned",
        activation: str = "gelu",
        **kwargs,
    ):
        super().__init__()
        self.tok_emb = nn.Embedding(VOCAB_SIZE, dim)
        pos_emb_size = (
            PC_MAX_POS if pos_encoding == "position_coupling" else max_seq_len
        )
        self.pos_emb = nn.Embedding(pos_emb_size, dim)
        self.layers = [
            TransformerBlock(dim, n_heads, ff_dim, activation=activation)
            for _ in range(n_layers)
        ]
        self.norm = RMSNorm(dim)
        self.output = nn.Linear(dim, VOCAB_SIZE, bias=False)
        self.max_seq_len = max_seq_len
        self.pos_encoding = pos_encoding

    def __call__(self, x, position_ids=None, return_all_logits=False):
        B, T = x.shape
        if position_ids is not None:
            positions = position_ids
        else:
            positions = mx.arange(T)
        h = self.tok_emb(x) + self.pos_emb(positions)

        # Causal mask
        mask = mx.triu(mx.full((T, T), float("-inf")), k=1)

        for layer in self.layers:
            h = layer(h, mask=mask)
        h = self.norm(h)
        return self.output(h)
