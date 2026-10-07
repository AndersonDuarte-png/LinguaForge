"""Lifecycle de processo por plataforma, sem llama.cpp real."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from linguaforge.config import get_config
from linguaforge.desktop_runtime import DesktopStartupError, ManagedModel, start_or_reuse_model
from linguaforge.platform import linux, windows

_SLEEPER = "import sys, time\ntime.sleep(float(sys.argv[1]))\n"

_FAKE_SERVER = '''\
import http.server, sys
port = int(sys.argv[1])
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
    def log_message(self, *args):
        pass
http.server.HTTPServer(("127.0.0.1", port), Handler).serve_forever()
'''


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


# ---- prepare_environment: funções puras testáveis em qualquer SO ----

def test_linux_prepare_environment_adds_ld_library_path(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = linux.prepare_environment(runtime, {"PATH": "/usr/bin"})
    assert env["LD_LIBRARY_PATH"] == str(runtime)
    assert env["PATH"] == "/usr/bin"


def test_linux_prepare_environment_preserves_existing_ld_library_path(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = linux.prepare_environment(runtime, {"LD_LIBRARY_PATH": "/opt/cuda"})
    assert env["LD_LIBRARY_PATH"] == f"{runtime}:/opt/cuda"


def test_linux_prepare_environment_ignores_missing_runtime(tmp_path):
    env = linux.prepare_environment(tmp_path / "missing", {})
    assert "LD_LIBRARY_PATH" not in env


def test_windows_prepare_environment_never_sets_ld_library_path(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = windows.prepare_environment(runtime, {"LD_LIBRARY_PATH": "/existing"})
    assert env == {"LD_LIBRARY_PATH": "/existing"}


# ---- Linux: spawn/terminate diretos (somente POSIX) ----

@pytest.mark.skipif(sys.platform == "win32", reason="Implementação Linux usa killpg/SIGTERM.")
def test_linux_spawn_and_terminate(tmp_path):
    script = tmp_path / "sleeper.py"
    script.write_text("#!/usr/bin/env python3\n" + _SLEEPER)
    script.chmod(0o755)
    process = linux.spawn_process([str(script), "120"], stdout=subprocess.DEVNULL, env=os.environ.copy())
    try:
        assert process.poll() is None
        linux.terminate_process(process)
        assert process.poll() is not None
        linux.terminate_process(process)  # idempotente
    finally:
        if process.poll() is None:
            process.kill()


# ---- Windows: spawn/terminate diretos (somente Windows) ----

@pytest.mark.skipif(sys.platform != "win32", reason="Lifecycle do processo é específico do Windows.")
def test_windows_spawn_starts_and_terminate_kills(tmp_path):
    script = tmp_path / "sleeper.py"
    script.write_text(_SLEEPER)
    log = (tmp_path / "log.txt").open("ab")
    process = windows.spawn_process(
        [sys.executable, str(script), "120"], stdout=log, env=os.environ.copy()
    )
    log.close()
    try:
        assert process.poll() is None  # vivo após o spawn
        windows.terminate_process(process)
        assert process.poll() is not None  # encerrado
        windows.terminate_process(process)  # idempotente
    finally:
        if process.poll() is None:
            process.kill()


@pytest.mark.skipif(sys.platform != "win32", reason="Lifecycle do processo é específico do Windows.")
def test_windows_managed_model_close_terminates_owned(tmp_path):
    script = tmp_path / "sleeper.py"
    script.write_text(_SLEEPER)
    process = windows.spawn_process(
        [sys.executable, str(script), "120"], stdout=subprocess.DEVNULL, env=os.environ.copy()
    )
    model = ManagedModel(process, "http://127.0.0.1:1")
    try:
        assert model.owned
        model.close()
        assert process.poll() is not None
        model.close()  # idempotente quando já encerrado
    finally:
        if process.poll() is None:
            process.kill()


def test_managed_model_close_ignores_reused_model():
    model = ManagedModel(None, "http://127.0.0.1:1")
    assert not model.owned
    model.close()  # não deve falhar nem encerrar nada


# ---- start_or_reuse_model: orquestração comum com processo real ----

def _fake_spawn(script: Path, spawned: list):
    def spawn(command, *, stdout, env):
        port = command[command.index("--port") + 1]
        process = subprocess.Popen(
            [sys.executable, str(script), port], stdout=stdout, stderr=subprocess.STDOUT, env=env
        )
        spawned.append(process)
        return process

    return spawn


def _server_config(tmp_path: Path):
    model_path = tmp_path / "model.gguf"
    model_path.touch()
    server = tmp_path / "llama-server"
    server.touch()
    return replace(
        get_config(installed=False),
        llama_server_path=server,
        model_path=model_path,
        state_dir=tmp_path / "state",
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Lifecycle do processo é específico do Windows.")
def test_windows_owned_model_starts_and_closes(tmp_path, monkeypatch):
    server_script = tmp_path / "fake-server.py"
    server_script.write_text(_FAKE_SERVER)
    spawned = []
    monkeypatch.setattr("linguaforge.platform.spawn_process", _fake_spawn(server_script, spawned))

    port = _free_port()
    managed = start_or_reuse_model(_server_config(tmp_path), port=port, timeout=5)
    try:
        assert managed.owned
        assert spawned[0].poll() is None
    finally:
        managed.close()
        assert spawned[0].poll() is not None


@pytest.mark.skipif(sys.platform != "win32", reason="Lifecycle do processo é específico do Windows.")
def test_windows_startup_failure_terminates_owned_process(tmp_path, monkeypatch):
    stuck = tmp_path / "stuck.py"
    stuck.write_text(_SLEEPER)
    spawned = []

    def spawn(command, *, stdout, env):
        process = subprocess.Popen(
            [sys.executable, str(stuck), "120"], stdout=stdout, stderr=subprocess.STDOUT, env=env
        )
        spawned.append(process)
        return process

    monkeypatch.setattr("linguaforge.platform.spawn_process", spawn)
    monkeypatch.setattr("linguaforge.desktop_runtime.is_healthy", lambda *_a, **_k: False)

    with pytest.raises(DesktopStartupError):
        start_or_reuse_model(_server_config(tmp_path), port=_free_port(), timeout=0.4)

    assert spawned and spawned[0].poll() is not None


def test_gpu_layers_default_and_env_priority(tmp_path, monkeypatch):
    """Default vem da plataforma; LLAMA_GPU_LAYERS explícita tem prioridade."""
    from linguaforge import platform

    model_path = tmp_path / "model.gguf"
    model_path.touch()
    server = tmp_path / "llama-server"
    server.touch()
    server.chmod(0o755)
    config = replace(
        get_config(installed=False),
        llama_server_path=server,
        model_path=model_path,
        state_dir=tmp_path / "state",
    )

    captured: dict[str, list[str]] = {}

    def spawn(command, *, stdout, env):
        captured["command"] = list(command)
        return subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=stdout,
            stderr=subprocess.STDOUT,
            env=env,
        )

    calls = {"n": 0}

    def healthy(base_url, timeout=1.0):
        calls["n"] += 1
        return calls["n"] > 1  # reuse check: False; wait_for_health: True

    monkeypatch.setattr("linguaforge.desktop_runtime.is_healthy", healthy)
    monkeypatch.setattr("linguaforge.platform.spawn_process", spawn)

    managed = start_or_reuse_model(config, timeout=1)
    managed.close()
    index = captured["command"].index("--gpu-layers")
    assert captured["command"][index + 1] == platform.default_gpu_layers()

    monkeypatch.setenv("LLAMA_GPU_LAYERS", "7")
    captured.clear()
    calls["n"] = 0
    managed = start_or_reuse_model(config, timeout=1)
    managed.close()
    index = captured["command"].index("--gpu-layers")
    assert captured["command"][index + 1] == "7"
