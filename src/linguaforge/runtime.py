from dataclasses import dataclass
from typing import Literal

from linguaforge.config import Config


@dataclass(frozen=True)
class Runtime:
    """Execution state with an explicitly selected device."""

    device: Literal["cpu", "cuda"]

    def __post_init__(self) -> None:
        if self.device not in ("cpu", "cuda"):
            raise ValueError("Runtime device must be 'cpu' or 'cuda'.")


def resolve_runtime(config: Config, *, cuda_available: bool) -> Runtime:
    """Resolve the requested device using availability supplied by the caller."""
    if config.device == "cpu":
        return Runtime(device="cpu")
    if config.device == "auto":
        return Runtime(device="cuda" if cuda_available else "cpu")
    if config.device == "cuda":
        if not cuda_available:
            raise RuntimeError("CUDA was requested but is not available.")
        return Runtime(device="cuda")
    raise ValueError(f"Unsupported configured device: {config.device!r}")
