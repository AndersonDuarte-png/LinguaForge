"""Comportamentos específicos do Windows."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from linguaforge.platform._types import LockNotAvailable, UserDirs

_APP_NAME = "LinguaForge"
_WAIT_OBJECT_0 = 0


def _appdata_dir(name: str, fallback: Path) -> Path:
    """Usa variáveis nativas e ignora valores relativos, como no Linux."""
    value = os.environ.get(name)
    path = Path(value) if value else fallback
    return path if path.is_absolute() else fallback


def resolve_user_dirs() -> UserDirs:
    """Resolve dados locais e configuração em diretórios nativos do usuário."""
    home = Path.home()
    local = _appdata_dir("LOCALAPPDATA", home / "AppData" / "Local")
    roaming = _appdata_dir("APPDATA", home / "AppData" / "Roaming")
    data_dir = local / _APP_NAME
    return UserDirs(
        data_dir=data_dir,
        config_dir=roaming / _APP_NAME,
        state_dir=data_dir / "state",
    )


def webview_gui() -> str | None:
    """Deixa o pywebview escolher o backend nativo (WebView2)."""
    return None


def _kernel32():
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateSemaphoreW.argtypes = (ctypes.c_void_p, ctypes.c_long, ctypes.c_long, ctypes.c_wchar_p)
    kernel32.CreateSemaphoreW.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
    kernel32.WaitForSingleObject.restype = ctypes.c_ulong
    kernel32.ReleaseSemaphore.argtypes = (ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p)
    kernel32.ReleaseSemaphore.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    return kernel32


class FileLock:
    """Lock de instância única baseado em semáforo nomeado do Windows."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle = None

    def _name(self) -> str:
        digest = hashlib.sha256(str(self.path.parent).lower().encode("utf-8")).hexdigest()
        return f"Local\\LinguaForge-{digest}"

    def acquire(self) -> None:
        kernel32 = _kernel32()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = kernel32.CreateSemaphoreW(None, 1, 1, self._name())
        if not handle:
            raise OSError("Não foi possível criar o lock de instância única.")
        if kernel32.WaitForSingleObject(handle, 0) != _WAIT_OBJECT_0:
            kernel32.CloseHandle(handle)
            raise LockNotAvailable()
        self._handle = handle
        try:
            self.path.write_text(str(os.getpid()))
        except OSError:
            pass  # O arquivo é apenas diagnóstico; o semáforo é a autoridade.

    def release(self) -> None:
        if self._handle is None:
            return
        kernel32 = _kernel32()
        kernel32.ReleaseSemaphore(self._handle, 1, None)
        kernel32.CloseHandle(self._handle)
        self._handle = None
