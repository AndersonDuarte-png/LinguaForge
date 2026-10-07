"""Comportamentos específicos do Linux."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess

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


def prepare_environment(cuda_runtime_dir: Path, base_env: dict[str, str]) -> dict[str, str]:
    """Expõe o runtime CUDA via LD_LIBRARY_PATH somente no processo filho."""
    environment = base_env.copy()
    if cuda_runtime_dir.is_dir():
        environment["LD_LIBRARY_PATH"] = f"{cuda_runtime_dir}:{environment.get('LD_LIBRARY_PATH', '')}".rstrip(":")
    return environment


def spawn_process(command: list[str], *, stdout, env: dict[str, str]) -> subprocess.Popen[bytes]:
    """Inicia o processo em sessão própria para permitir encerrar o grupo."""
    return subprocess.Popen(
        command, stdout=stdout, stderr=subprocess.STDOUT, env=env, start_new_session=True
    )


def terminate_process(
    process: subprocess.Popen[bytes], *, graceful_timeout: float = 8.0, force_timeout: float = 3.0
) -> None:
    """SIGTERM no grupo do processo; SIGKILL como fallback após o timeout."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=graceful_timeout)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=force_timeout)


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
