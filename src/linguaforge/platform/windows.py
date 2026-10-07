"""Comportamentos específicos do Windows."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

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


def valid_server_names() -> tuple[str, ...]:
    """Nomes aceitos para o executável do llama.cpp no Windows."""
    return ("llama-server.exe", "llama-server")


def development_backend_dir(data_dir: Path) -> Path:
    """Backend de desenvolvimento padrão no Windows (Vulkan)."""
    return data_dir / "llama.cpp" / "b10978" / "win-vulkan-x64"


def cpu_backend_dir(data_dir: Path) -> Path:
    """Backend CPU de desenvolvimento, preservado para o fallback do W3-C."""
    return data_dir / "llama.cpp" / "b10978" / "win-cpu-x64"


def default_server_path(backend_dir: Path) -> Path:
    """Caminho padrão do executável dentro do backend de desenvolvimento."""
    return backend_dir / "llama-server.exe"


def default_gpu_layers() -> str:
    """Offload padrão no Windows (Vulkan primário, offload completo)."""
    return "999"


def prepare_environment(cuda_runtime_dir: Path, base_env: dict[str, str]) -> dict[str, str]:
    """O Windows não usa LD_LIBRARY_PATH; o ambiente é repassado sem alterações."""
    return base_env.copy()


def spawn_process(command: list[str], *, stdout, env: dict[str, str]) -> subprocess.Popen[bytes]:
    """Inicia o processo sem abrir janela de console."""
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        command, stdout=stdout, stderr=subprocess.STDOUT, env=env, creationflags=creationflags
    )


def terminate_process(
    process: subprocess.Popen[bytes], *, graceful_timeout: float = 8.0, force_timeout: float = 3.0
) -> None:
    """TerminateProcess imediato; kill() como fallback idempotente."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=graceful_timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=force_timeout)
        except subprocess.TimeoutExpired:
            pass


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
