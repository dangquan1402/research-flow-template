"""Encoder-decoder arithmetic transformer (MLX).

Uses a "prefix LM" approach for efficiency: both encoder and decoder operate on
the full sequence, but with different attention masks. The encoder uses
bidirectional attention over the prefix (up to and including '='), while the
decoder uses causal attention over the full sequence with cross-attention to
encoder outputs. This avoids per-sample Python loops entirely.
"""

import math

import mlx.core as mx
import mlx.nn as nn

from ..tokenizer import PC_MAX_POS, TOK2ID, VOCAB_SIZE
from . import register_model
from .base import FeedForward, MultiHeadAttention, RMSNorm, TransformerBlock

EQ_ID = TOK2ID["="]


class CrossAttention(nn.Module):
    """Cross-attention: queries from decoder, keys/values from encoder."""

    def __init__(self, dim: int, n_heads: int):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.wq = nn.Linear(dim, dim, bias=False)
        self.wk = nn.Linear(dim, dim, bias=False)
        self.wv = nn.Linear(dim, dim, bias=False)
        self.wo = nn.Linear(dim, dim, bias=False)

    def __call__(self, x, enc_out, enc_mask=None):
        B, T, C = x.shape
        _, S, _ = enc_out.shape

        q = self.wq(x).reshape(B, T, self.n_heads, self.head_dim).transpose(0, 2, 1, 3)
        k = (
            self.wk(enc_out)
            .reshape(B, S, self.n_heads, self.head_dim)
            .transpose(0, 2, 1, 3)
        )
        v = (
            self.wv(enc_out)
            .reshape(B, S, self.n_heads, self.head_dim)
            .transpose(0, 2, 1, 3)
        )

        scale = math.sqrt(self.head_dim)
        attn = (q @ k.transpose(0, 1, 3, 2)) / scale

        if enc_mask is not None:
            attn = attn + enc_mask

        attn = mx.softmax(attn, axis=-1)
        out = (attn @ v).transpose(0, 2, 1, 3).reshape(B, T, C)
        return self.wo(out)


class DecoderBlock(nn.Module):
    """Decoder block: causal self-attention + cross-attention + FFN."""

    def __init__(self, dim: int, n_heads: int, ff_dim: int, activation: str = "gelu"):
        super().__init__()
        self.norm1 = RMSNorm(dim)
        self.self_attn = MultiHeadAttention(dim, n_heads)
        self.norm2 = RMSNorm(dim)
        self.cross_attn = CrossAttention(dim, n_heads)
        self.norm3 = RMSNorm(dim)
        self.ff = FeedForward(dim, ff_dim, activation_name=activation)

    def __call__(self, x, causal_mask, enc_out, enc_mask=None):
        x = x + self.self_attn(self.norm1(x), mask=causal_mask)
        x = x + self.cross_attn(self.norm2(x), enc_out, enc_mask=enc_mask)
        x = x + self.ff(self.norm3(x))
        return x


@register_model("encoder_decoder")
class EncoderDecoderTransformer(nn.Module):
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

        # Encoder: bidirectional transformer blocks
        self.encoder_layers = [
            TransformerBlock(dim, n_heads, ff_dim, activation=activation)
            for _ in range(n_layers)
        ]
        self.encoder_norm = RMSNorm(dim)

        # Decoder: self-attn + cross-attn + FFN blocks
        self.decoder_layers = [
            DecoderBlock(dim, n_heads, ff_dim, activation=activation)
            for _ in range(n_layers)
        ]
        self.decoder_norm = RMSNorm(dim)

        self.output = nn.Linear(dim, VOCAB_SIZE, bias=False)
        self.max_seq_len = max_seq_len
        self.pos_encoding = pos_encoding

    def __call__(self, x, position_ids=None, return_all_logits=False):
        B, T = x.shape

        # Positions
        if position_ids is not None:
            positions = position_ids
        else:
            positions = mx.arange(T)

        # Embed full sequence
        h = self.tok_emb(x) + self.pos_emb(positions)

        # Find '=' position per sample (vectorized)
        eq_mask = x == EQ_ID  # (B, T)
        eq_positions = mx.argmax(eq_mask.astype(mx.int32), axis=1)  # (B,)

        # Build encoder attention mask: any row can attend to prefix columns
        # (positions <= eq_pos). Non-prefix columns are masked out.
        # This avoids all-inf rows for positions after '='.
        # Shape: (B, 1, 1, T)
        col_idx = mx.arange(T).reshape(1, T)  # (1, T)
        eq_pos = eq_positions.reshape(B, 1)  # (B, 1)

        is_enc_col = col_idx <= eq_pos  # (B, T)
        enc_attn_mask = mx.where(
            is_enc_col.reshape(B, 1, 1, T),
            mx.array(0.0),
            mx.array(float("-inf")),
        )

        # Encoder forward (full sequence, masked)
        enc_h = h
        for layer in self.encoder_layers:
            enc_h = layer(enc_h, mask=enc_attn_mask)
        enc_h = self.encoder_norm(enc_h)

        # Decoder causal mask (standard)
        dec_causal = mx.triu(mx.full((T, T), float("-inf")), k=1)

        # Cross-attention mask: decoder can attend to encoder positions <= eq_pos
        # Reuse encoder column mask (same shape: B, 1, 1, T)
        cross_mask = enc_attn_mask

        # Decoder forward
        dec_h = h  # start from same embeddings
        for layer in self.decoder_layers:
            dec_h = layer(dec_h, dec_causal, enc_h, enc_mask=cross_mask)
        dec_h = self.decoder_norm(dec_h)

        return self.output(dec_h)
