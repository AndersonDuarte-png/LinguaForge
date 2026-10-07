"""Ciclo de vida dos processos usados pela janela desktop instalada."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import socket
import subprocess
import time
import json
from urllib.request import Request, urlopen
from collections.abc import Callable

from linguaforge import platform
from linguaforge.config import Config
from linguaforge.platform import ModelBackend

_logger = logging.getLogger(__name__)


class DesktopStartupError(RuntimeError):
    """Erro que pode ser mostrado ao usuário na janela desktop."""


@dataclass
class ManagedModel:
    """Modelo local iniciado por esta sessão ou reutilizado de outra sessão."""

    process: subprocess.Popen[bytes] | None
    base_url: str
    backend: str | None = None

    @property
    def owned(self) -> bool:
        return self.process is not None

    def close(self) -> None:
        """Encerra somente o processo iniciado por esta sessão."""
        if self.process is None:
            return
        platform.terminate_process(self.process)


class InstanceLock:
    """Impede duas janelas instaladas de usarem os mesmos recursos."""

    def __init__(self, state_dir: Path) -> None:
        self._lock = platform.FileLock(state_dir / "linguaforge.lock")

    def __enter__(self) -> "InstanceLock":
        try:
            self._lock.acquire()
        except platform.LockNotAvailable as error:
            raise DesktopStartupError("LinguaForge is already running.") from error
        return self

    def __exit__(self, *_: object) -> None:
        self._lock.release()


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


def _start_backend(
    config: Config,
    backend: ModelBackend,
    *,
    base_url: str,
    host: str,
    port: int,
    timeout: float,
    on_process: Callable[[ManagedModel], None] | None,
) -> ManagedModel:
    """Inicia um backend e aguarda saúde; limpa o processo owned em caso de falha."""
    server_path = backend.server_path
    if not server_path.is_file():
        raise DesktopStartupError(f"Arquivo necessário não encontrado: {server_path}")
    if not os.access(server_path, os.X_OK):
        raise DesktopStartupError(f"O backend não tem permissão de execução: {server_path}")
    config.state_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.state_dir / "llama-server.log"
    environment = platform.prepare_environment(config.cuda_runtime_dir, os.environ.copy())
    command = [
        str(server_path),
        "--model", str(config.model_path),
        "--host", host,
        "--port", str(port),
        "--gpu-layers", os.environ.get("LLAMA_GPU_LAYERS", backend.gpu_layers),
        "--ctx-size", os.environ.get("LLAMA_CONTEXT_SIZE", "4096"),
        "--parallel", os.environ.get("LLAMA_PARALLEL_SLOTS", "1"),
    ]
    log = log_path.open("ab")
    process = platform.spawn_process(command, stdout=log, env=environment)
    log.close()
    managed = ManagedModel(process, base_url, backend=backend.name)
    if on_process is not None:
        on_process(managed)
    try:
        _wait_for_health(base_url, process, timeout)
    except Exception:
        managed.close()
        raise
    return managed


def start_or_reuse_model(
    config: Config,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    timeout: float = 120.0,
    on_process: Callable[[ManagedModel], None] | None = None,
) -> ManagedModel:
    """Reutiliza um servidor saudável ou inicia o modelo local sem downloads.

    No Windows, os backends gerenciados pela plataforma são tentados em ordem
    (Vulkan primário, CPU fallback). Configurações explícitas do usuário e erros
    compartilhados (GGUF ausente, porta ocupada) não disparam fallback.
    """
    base_url = f"http://{host}:{port}"
    if is_healthy(base_url):
        return ManagedModel(None, base_url)
    if not _port_is_free(host, port):
        raise DesktopStartupError(f"A porta do llama-server está ocupada: {host}:{port}.")
    if not config.model_path.is_file():
        raise DesktopStartupError(f"Arquivo necessário não encontrado: {config.model_path}")

    if config.llama_server_is_explicit:
        backend = ModelBackend("explicit", config.llama_server_path, platform.default_gpu_layers())
        return _start_backend(
            config, backend, base_url=base_url, host=host, port=port, timeout=timeout, on_process=on_process
        )

    failures: list[str] = []
    for backend in platform.model_backends(config.data_dir):
        _logger.info("tentando backend %s", backend.name)
        try:
            managed = _start_backend(
                config, backend, base_url=base_url, host=host, port=port, timeout=timeout, on_process=on_process
            )
            _logger.info("backend %s disponível", backend.name)
            return managed
        except DesktopStartupError as error:
            _logger.warning("backend %s falhou: %s", backend.name, error)
            failures.append(f"{backend.name}: {error}")
    raise DesktopStartupError("Não foi possível iniciar o modelo local. " + " | ".join(failures))
