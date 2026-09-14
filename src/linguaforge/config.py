from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    project_root: Path
    data_dir: Path
    models_dir: Path
    device: str = "auto"
    interface_language: str = "pt-BR"
    target_language: str = "en"


def get_config() -> Config:
    # project_root is two parents above this file: linguaforge -> src -> project root
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    models_dir = project_root / "models"

    return Config(
        project_root=project_root,
        data_dir=data_dir,
        models_dir=models_dir,
    )


# Module-level default config instance
config = get_config()
