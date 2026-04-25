"""Model registry for arithmetic transformer architectures."""

MODEL_REGISTRY = {}


def register_model(name):
    def decorator(cls):
        MODEL_REGISTRY[name] = cls
        return cls
    return decorator


def get_model(name, **kwargs):
    if name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {name}. Available: {list(MODEL_REGISTRY.keys())}"
        )
    return MODEL_REGISTRY[name](**kwargs)


# Auto-import to trigger registration
from . import decoder_only as decoder_only  # noqa: E402
from . import encoder_decoder as encoder_decoder
from . import looped as looped
