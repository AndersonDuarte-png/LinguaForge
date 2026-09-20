from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    project_root: Path
    data_dir: Path
    models_dir: Path
    device: str = "auto"
    interface_language: str = "en"
    target_language: str = "en"


def get_config() -> Config:
    # A raiz do projeto fica dois níveis acima deste arquivo: linguaforge -> src -> projeto.
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    models_dir = project_root / "models"

    return Config(
        project_root=project_root,
        data_dir=data_dir,
        models_dir=models_dir,
    )


# Instância de configuração padrão do módulo.
config = get_config()
