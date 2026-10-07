"""Comportamentos específicos do Linux."""

from __future__ import annotations

import os
from pathlib import Path

from linguaforge.platform._types import LockNotAvailable, UserDirs


def _xdg_path(name: str, fallback: Path) -> Path:
    """Ignora caminhos XDG relativos, conforme a especificação."""
    value = os.environ.get(name)
    path = Path(value) if value else fallback
    return path if path.is_absolute() else fallback


def resolve_user_dirs() -> UserDirs:
    """Resolve data/config/state via XDG, sem criar diretórios."""
    home = Path.home()
    return UserDirs(
        data_dir=_xdg_path("XDG_DATA_HOME", home / ".local" / "share") / "linguaforge",
        config_dir=_xdg_path("XDG_CONFIG_HOME", home / ".config") / "linguaforge",
        state_dir=_xdg_path("XDG_STATE_HOME", home / ".local" / "state") / "linguaforge",
    )


def webview_gui() -> str | None:
    """Backend do pywebview usado no Linux."""
    return "gtk"


class FileLock:
    """Lock de instância única baseado em flock."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None

    def acquire(self) -> None:
        import fcntl  # disponível apenas no Linux.

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self._file.close()
            self._file = None
            raise LockNotAvailable() from error
        self._file.seek(0)
        self._file.truncate()
        self._file.write(str(os.getpid()))
        self._file.flush()

    def release(self) -> None:
        if self._file is None:
            return
        import fcntl  # disponível apenas no Linux.

        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
        self._file = None
