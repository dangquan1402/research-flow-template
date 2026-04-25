"""Framework detection (MLX vs PyTorch) and device setup."""

import importlib.util

FRAMEWORK = None

if importlib.util.find_spec("mlx") is not None:
    FRAMEWORK = "mlx"
elif importlib.util.find_spec("torch") is not None:
    import torch

    if not torch.backends.mps.is_available():
        print("WARNING: PyTorch MPS not available, using CPU")
    FRAMEWORK = "pytorch"
else:
    raise RuntimeError("Neither MLX nor PyTorch is installed")

print(f"Using framework: {FRAMEWORK}")
