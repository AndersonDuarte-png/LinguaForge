from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Runtime:
    """Execution state with an explicitly selected device."""

    device: Literal["cpu", "cuda"]

    def __post_init__(self) -> None:
        if self.device not in ("cpu", "cuda"):
            raise ValueError("Runtime device must be 'cpu' or 'cuda'.")
