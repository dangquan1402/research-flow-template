"""ReLU² activation."""

import mlx.core as mx

from . import register_activation


@register_activation("relu_squared")
def relu_squared_activation(x, nn_module):
    """ReLU squared: max(0, x)²."""
    return mx.maximum(x, 0) ** 2
