"""Tipos compartilhados pelas implementações de plataforma."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class LockNotAvailable(OSError):
    """O lock de instância única já pertence a outro processo."""


@dataclass(frozen=True)
class UserDirs:
    """Diretórios graváveis da aplicação instalada."""

    data_dir: Path
    config_dir: Path
    state_dir: Path
