"""Shared model components: RMSNorm, MultiHeadAttention, FeedForward, TransformerBlock (MLX)."""

import math

import mlx.core as mx
import mlx.nn as nn

from ..activations import get_activation


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = mx.ones((dim,))
        self.eps = eps

    def __call__(self, x):
        rms = mx.sqrt(mx.mean(x * x, axis=-1, keepdims=True) + self.eps)
        return x / rms * self.weight


class MultiHeadAttention(nn.Module):
    def __init__(self, dim: int, n_heads: int):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.wq = nn.Linear(dim, dim, bias=False)
        self.wk = nn.Linear(dim, dim, bias=False)
        self.wv = nn.Linear(dim, dim, bias=False)
        self.wo = nn.Linear(dim, dim, bias=False)

    def __call__(self, x, mask=None):
        B, T, C = x.shape
        q = (
            self.wq(x)
            .reshape(B, T, self.n_heads, self.head_dim)
            .transpose(0, 2, 1, 3)
        )
        k = (
            self.wk(x)
            .reshape(B, T, self.n_heads, self.head_dim)
            .transpose(0, 2, 1, 3)
        )
        v = (
            self.wv(x)
            .reshape(B, T, self.n_heads, self.head_dim)
            .transpose(0, 2, 1, 3)
        )

        scale = math.sqrt(self.head_dim)
        attn = (q @ k.transpose(0, 1, 3, 2)) / scale

        if mask is not None:
            attn = attn + mask

        attn = mx.softmax(attn, axis=-1)
        out = (attn @ v).transpose(0, 2, 1, 3).reshape(B, T, C)
        return self.wo(out)


class FeedForward(nn.Module):
    def __init__(self, dim: int, ff_dim: int, activation_name: str = "gelu"):
        super().__init__()
        self.activation_name = activation_name
        self.act_fn = get_activation(activation_name)
        if activation_name == "swiglu":
            self.w_gate = nn.Linear(dim, ff_dim, bias=False)
            self.w_up = nn.Linear(dim, ff_dim, bias=False)
            self.w2 = nn.Linear(ff_dim, dim, bias=False)
        else:
            self.w1 = nn.Linear(dim, ff_dim, bias=False)
            self.w2 = nn.Linear(ff_dim, dim, bias=False)

    def __call__(self, x):
        if self.activation_name == "swiglu":
            return self.w2(self.act_fn(x, self))
        else:
            return self.w2(self.act_fn(self.w1(x), self))


class TransformerBlock(nn.Module):
    def __init__(self, dim: int, n_heads: int, ff_dim: int, activation: str = "gelu"):
        super().__init__()
        self.norm1 = RMSNorm(dim)
        self.attn = MultiHeadAttention(dim, n_heads)
        self.norm2 = RMSNorm(dim)
        self.ff = FeedForward(dim, ff_dim, activation_name=activation)

    def __call__(self, x, mask=None):
        x = x + self.attn(self.norm1(x), mask=mask)
        x = x + self.ff(self.norm2(x))
        return x
