"""GELU activation (default)."""

from . import register_activation


@register_activation("gelu")
def gelu_activation(x, nn_module):
    """Standard GELU activation. Uses MLX nn.gelu."""
    import mlx.nn as nn

    return nn.gelu(x)
