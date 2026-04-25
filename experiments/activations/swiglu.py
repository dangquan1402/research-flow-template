"""SwiGLU activation."""

from . import register_activation


@register_activation("swiglu")
def swiglu_activation(x, nn_module):
    """SwiGLU: uses gate and up projections from the FeedForward module."""
    import mlx.nn as nn

    return nn.silu(nn_module.w_gate(x)) * nn_module.w_up(x)
