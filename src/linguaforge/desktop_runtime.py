"""Ciclo de vida dos processos usados pela janela desktop instalada."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import json
from urllib.request import Request, urlopen
from collections.abc import Callable

from linguaforge.config import Config


class DesktopStartupError(RuntimeError):
    """Erro que pode ser mostrado ao usuário na janela desktop."""


@dataclass
class ManagedModel:
    """Modelo local iniciado por esta sessão ou reutilizado de outra sessão."""

    process: subprocess.Popen[bytes] | None
    base_url: str

    @property
    def owned(self) -> bool:
        return self.process is not None

    def close(self) -> None:
        """Encerra somente o processo iniciado por esta sessão."""
        if self.process is None or self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=8)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=3)


class InstanceLock:
    """Impede duas janelas instaladas de usarem os mesmos recursos."""

    def __init__(self, state_dir: Path) -> None:
        self.path = state_dir / "linguaforge.lock"
        self._file = None

    def __enter__(self) -> "InstanceLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self._file.close()
            self._file = None
            raise DesktopStartupError("LinguaForge is already running.") from error
        self._file.seek(0)
        self._file.truncate()
        self._file.write(str(os.getpid()))
        self._file.flush()
        return self

    def __exit__(self, *_: object) -> None:
        if self._file is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._file.close()
            self._file = None


def is_healthy(base_url: str, timeout: float = 1.0) -> bool:
    request = Request(f"{base_url.rstrip('/')}/health")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(8192))
            return response.status == 200 and isinstance(payload, dict) and payload.get("status") == "ok"
    except (OSError, ValueError):
        return False


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((host, port))
        except OSError:
            return False
    return True


def _wait_for_health(base_url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise DesktopStartupError("llama-server encerrou durante a inicialização.")
        if is_healthy(base_url):
            return
        time.sleep(0.2)
    raise DesktopStartupError("O modelo não ficou disponível dentro do tempo esperado.")


def start_or_reuse_model(
    config: Config,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    timeout: float = 120.0,
    on_process: Callable[[ManagedModel], None] | None = None,
) -> ManagedModel:
    """Reutiliza um servidor saudável ou inicia o modelo local sem downloads."""
    base_url = f"http://{host}:{port}"
    if is_healthy(base_url):
        return ManagedModel(None, base_url)
    if not _port_is_free(host, port):
        raise DesktopStartupError(f"A porta do llama-server está ocupada: {host}:{port}.")
    for required in (config.llama_server_path, config.model_path):
        if not required.is_file():
            raise DesktopStartupError(f"Arquivo necessário não encontrado: {required}")
    if not os.access(config.llama_server_path, os.X_OK):
        raise DesktopStartupError(f"O backend não tem permissão de execução: {config.llama_server_path}")
    config.state_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.state_dir / "llama-server.log"
    environment = os.environ.copy()
    if config.cuda_runtime_dir.is_dir():
        environment["LD_LIBRARY_PATH"] = f"{config.cuda_runtime_dir}:{environment.get('LD_LIBRARY_PATH', '')}".rstrip(":")
    command = [
        str(config.llama_server_path),
        "--model", str(config.model_path),
        "--host", host,
        "--port", str(port),
        "--gpu-layers", os.environ.get("LLAMA_GPU_LAYERS", "999"),
        "--ctx-size", os.environ.get("LLAMA_CONTEXT_SIZE", "4096"),
        "--parallel", os.environ.get("LLAMA_PARALLEL_SLOTS", "1"),
    ]
    log = log_path.open("ab")
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment, start_new_session=True)
    log.close()
    managed = ManagedModel(process, base_url)
    if on_process is not None:
        on_process(managed)
    try:
        _wait_for_health(base_url, process, timeout)
    except Exception:
        managed.close()
        raise
    return managed
