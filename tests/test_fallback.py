"""Fallback automático Vulkan → CPU no Windows (orquestração sem GPU real)."""

from __future__ import annotations

import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from linguaforge.config import get_config
from linguaforge.desktop_runtime import DesktopStartupError, start_or_reuse_model
from linguaforge.platform import ModelBackend, linux, windows

_OK_SERVER = """\
import http.server, sys
port = int(sys.argv[1])
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
    def log_message(self, *args):
        pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
"""

_EXIT = "import sys\nsys.exit(3)\n"
_SLEEP = "import time\ntime.sleep(60)\n"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _spawn_kwargs() -> dict[str, bool]:
    """Imita `platform.spawn_process`: encerrar o grupo no Linux exige sessão própria."""
    return {} if sys.platform == "win32" else {"start_new_session": True}


def _config(tmp_path: Path):
    model = tmp_path / "model.gguf"
    model.touch()
    return replace(
        get_config(installed=False),
        model_path=model,
        state_dir=tmp_path / "state",
    )


def _marker(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.touch()
    path.chmod(0o755)
    return path


def _spawn_factory(tmp_path: Path, behaviors: dict[str, str], spawned: list, commands: list):
    """Simula spawn por backend: 'ok' serve /health, 'exit' sai, 'sleep' nunca fica saudável."""
    scripts: dict[str, Path] = {}

    def spawn(command, *, stdout, env):
        server = command[0]
        port = command[command.index("--port") + 1]
        commands.append(list(command))
        behavior = behaviors.get(server, "exit")
        script = scripts.get(behavior)
        if script is None:
            if behavior == "ok":
                script = tmp_path / "ok-server.py"
                script.write_text(_OK_SERVER)
            elif behavior == "exit":
                script = tmp_path / "exit.py"
                script.write_text(_EXIT)
            elif behavior == "sleep":
                script = tmp_path / "sleep.py"
                script.write_text(_SLEEP)
            else:
                raise AssertionError(f"comportamento desconhecido: {behavior}")
            scripts[behavior] = script
        process = subprocess.Popen(
            [sys.executable, str(script), port],
            stdout=stdout,
            stderr=subprocess.STDOUT,
            env=env,
            **_spawn_kwargs(),
        )
        spawned.append((server, process))
        return process

    return spawn


def _patch_backends(monkeypatch, tmp_path: Path, *, vulkan_exists: bool = True) -> tuple[Path, Path]:
    vulkan = _marker(tmp_path, "vulkan.exe") if vulkan_exists else tmp_path / "vulkan.exe"
    cpu = _marker(tmp_path, "cpu.exe")
    monkeypatch.setattr(
        "linguaforge.platform.model_backends",
        lambda _data_dir: (ModelBackend("vulkan", vulkan, "999"), ModelBackend("cpu", cpu, "0")),
    )
    return vulkan, cpu


def test_vulkan_healthy_does_not_try_cpu(tmp_path, monkeypatch):
    vulkan, cpu = _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    commands: list = []
    monkeypatch.setattr(
        "linguaforge.platform.spawn_process",
        _spawn_factory(tmp_path, {str(vulkan): "ok", str(cpu): "exit"}, spawned, commands),
    )

    managed = start_or_reuse_model(_config(tmp_path), port=_free_port(), timeout=5)
    try:
        assert managed.owned
        assert managed.backend == "vulkan"
        assert [server for server, _ in spawned] == [str(vulkan)]
    finally:
        managed.close()


def test_vulkan_missing_uses_cpu_fallback(tmp_path, monkeypatch):
    vulkan, cpu = _patch_backends(monkeypatch, tmp_path, vulkan_exists=False)
    spawned: list = []
    commands: list = []
    monkeypatch.setattr(
        "linguaforge.platform.spawn_process",
        _spawn_factory(tmp_path, {str(cpu): "ok"}, spawned, commands),
    )

    managed = start_or_reuse_model(_config(tmp_path), port=_free_port(), timeout=5)
    try:
        assert managed.owned
        assert managed.backend == "cpu"
        assert [server for server, _ in spawned] == [str(cpu)]
    finally:
        managed.close()


def test_vulkan_exits_then_cpu_succeeds_and_params_are_correct(tmp_path, monkeypatch):
    vulkan, cpu = _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    commands: list = []
    monkeypatch.setattr(
        "linguaforge.platform.spawn_process",
        _spawn_factory(tmp_path, {str(vulkan): "exit", str(cpu): "ok"}, spawned, commands),
    )

    managed = start_or_reuse_model(_config(tmp_path), port=_free_port(), timeout=5)
    try:
        assert managed.owned
        assert managed.backend == "cpu"
        vulkan_procs = [p for server, p in spawned if server == str(vulkan)]
        cpu_procs = [p for server, p in spawned if server == str(cpu)]
        assert vulkan_procs and vulkan_procs[0].poll() is not None  # limpo antes do CPU
        assert cpu_procs and cpu_procs[0].poll() is None  # CPU ativo e owned
    finally:
        managed.close()

    vulkan_cmd = next(c for c in commands if c[0] == str(vulkan))
    cpu_cmd = next(c for c in commands if c[0] == str(cpu))
    assert vulkan_cmd[vulkan_cmd.index("--gpu-layers") + 1] == "999"
    assert cpu_cmd[cpu_cmd.index("--gpu-layers") + 1] == "0"


def test_vulkan_timeout_then_cpu(tmp_path, monkeypatch):
    vulkan, cpu = _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    commands: list = []
    monkeypatch.setattr(
        "linguaforge.platform.spawn_process",
        _spawn_factory(tmp_path, {str(vulkan): "sleep", str(cpu): "ok"}, spawned, commands),
    )

    managed = start_or_reuse_model(_config(tmp_path), port=_free_port(), timeout=3)
    try:
        assert managed.owned
        assert managed.backend == "cpu"
        vulkan_procs = [p for server, p in spawned if server == str(vulkan)]
        assert vulkan_procs and vulkan_procs[0].poll() is not None
    finally:
        managed.close()


def test_both_backends_fail_no_process_and_combined_error(tmp_path, monkeypatch):
    vulkan, cpu = _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    commands: list = []
    monkeypatch.setattr(
        "linguaforge.platform.spawn_process",
        _spawn_factory(tmp_path, {str(vulkan): "exit", str(cpu): "exit"}, spawned, commands),
    )

    with pytest.raises(DesktopStartupError) as excinfo:
        start_or_reuse_model(_config(tmp_path), port=_free_port(), timeout=0.4)

    message = str(excinfo.value)
    assert "vulkan" in message and "cpu" in message
    assert spawned and all(process.poll() is not None for _, process in spawned)


def test_missing_gguf_fails_before_any_backend(tmp_path, monkeypatch):
    _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    monkeypatch.setattr("linguaforge.platform.spawn_process", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria spawnar")))
    config = replace(_config(tmp_path), model_path=tmp_path / "missing.gguf")

    with pytest.raises(DesktopStartupError, match="Arquivo necessário"):
        start_or_reuse_model(config, port=_free_port())

    assert not spawned


def test_port_occupied_does_not_try_fallback(tmp_path, monkeypatch):
    _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    monkeypatch.setattr("linguaforge.platform.spawn_process", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria spawnar")))
    monkeypatch.setattr("linguaforge.desktop_runtime._port_is_free", lambda *_a: False)

    with pytest.raises(DesktopStartupError, match="ocupada"):
        start_or_reuse_model(_config(tmp_path), port=12345)

    assert not spawned


def test_external_healthy_server_is_reused_and_not_closed(tmp_path, monkeypatch):
    _patch_backends(monkeypatch, tmp_path)
    spawned: list = []
    monkeypatch.setattr("linguaforge.platform.spawn_process", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria spawnar")))
    monkeypatch.setattr("linguaforge.desktop_runtime.is_healthy", lambda *_a, **_k: True)

    managed = start_or_reuse_model(_config(tmp_path), port=_free_port())
    assert not managed.owned
    assert managed.process is None
    managed.close()  # no-op para servidor externo
    assert not spawned


def test_explicit_server_is_not_replaced_by_cpu_fallback(tmp_path, monkeypatch):
    explicit = _marker(tmp_path, "explicit-server.exe")
    cpu = _marker(tmp_path, "cpu.exe")
    monkeypatch.setattr(
        "linguaforge.platform.model_backends",
        lambda _data_dir: (ModelBackend("vulkan", explicit, "999"), ModelBackend("cpu", cpu, "0")),
    )
    spawned: list = []
    commands: list = []
    monkeypatch.setattr(
        "linguaforge.platform.spawn_process",
        _spawn_factory(tmp_path, {str(explicit): "exit", str(cpu): "ok"}, spawned, commands),
    )
    config = replace(_config(tmp_path), llama_server_path=explicit, llama_server_is_explicit=True)

    with pytest.raises(DesktopStartupError):
        start_or_reuse_model(config, port=_free_port(), timeout=0.4)

    # Somente o servidor explícito foi tentado; CPU nunca foi usado.
    assert [server for server, _ in spawned] == [str(explicit)]


def test_windows_model_backends_order_and_params():
    data_dir = Path("D:/data")
    backends = windows.model_backends(data_dir)
    assert [backend.name for backend in backends] == ["vulkan", "cpu"]
    assert backends[0].gpu_layers == "999"
    assert backends[1].gpu_layers == "0"
    assert backends[0].server_path.name == "llama-server.exe"
    assert backends[1].server_path.name == "llama-server.exe"


def test_linux_model_backends_single_cuda():
    data_dir = Path("/data")
    backends = linux.model_backends(data_dir)
    assert len(backends) == 1
    assert backends[0].name == "cuda"
