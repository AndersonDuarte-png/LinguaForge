"""Exercita os launchers sem carregar modelos, abrir portas ou instalar pacotes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import select
import subprocess
import sys
import time

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o755)


@pytest.fixture
def launcher(tmp_path: Path):
    """Monta um projeto temporário que registra processos e chamadas HTTP falsas."""
    project = tmp_path / "project"
    shutil.copytree(SCRIPTS, project / "scripts")
    fake_bin = tmp_path / "bin"
    state = tmp_path / "state"
    state.mkdir()
    header = f"#!{sys.executable}\n"
    _executable(fake_bin / "node", "#!/bin/sh\nexit 0\n")
    _executable(fake_bin / "npm", header + '''import os, pathlib, sys
state = pathlib.Path(os.environ["FAKE_STATE"])
(state / "build").touch()
sys.exit(1 if os.environ.get("FAKE_BUILD_FAIL") else 0)
''')
    _executable(fake_bin / "curl", header + '''import json, os, pathlib, sys
state = pathlib.Path(os.environ["FAKE_STATE"])
with (state / "curl.jsonl").open("a") as output:
    output.write(json.dumps(sys.argv[1:]) + "\\n")
is_app = ":8000" in sys.argv[-1]
ready = ((state / "app").exists() or os.environ.get("FAKE_EXISTING_APP")) if is_app else ((state / "llama").exists() or os.environ.get("FAKE_EXISTING_LLAMA"))
if (is_app and os.environ.get("FAKE_APP_UNREADY")) or not ready:
    sys.exit(22)
print("{}" if os.environ.get("FAKE_BAD_HEALTH") else '{"status":"ok"}')
''')
    _executable(project / ".venv/bin/python", header + '''import os, sys
code = sys.argv[2] if len(sys.argv) > 2 else ""
if code == "import fastapi, uvicorn, linguaforge.web":
    sys.exit(0)
if "sock.bind" in code:
    sys.exit("A porta 8000 está ocupada.") if os.environ.get("FAKE_OCCUPIED") else sys.exit(0)
os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
''')
    _executable(project / ".venv/bin/linguaforge-web", "#!/bin/sh\nexit 0\n")
    _executable(project / "frontend/node_modules/.bin/vite", "#!/bin/sh\nexit 0\n")
    worker = header + '''import json, os, pathlib, signal, subprocess, sys, time
state = pathlib.Path(os.environ["FAKE_STATE"])
kind = "app" if pathlib.Path(sys.argv[0]).name == "uv" else "llama"
(state / (kind + ".pid")).write_text(str(os.getpid()))
(state / (kind + ".args")).write_text(json.dumps(sys.argv[1:]))
if os.environ.get("FAKE_FAIL") == kind:
    sys.exit(7)
child_code = "import time; time.sleep(60)"
if os.environ.get("FAKE_STUBBORN") == kind:
    child_code = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
child = subprocess.Popen([sys.executable, "-c", child_code])
(state / (kind + ".child.pid")).write_text(str(child.pid))
(state / kind).touch()
while True:
    time.sleep(0.1)
'''
    _executable(fake_bin / "uv", worker)
    _executable(project / "data/llama.cpp/b10978/cuda12.8/bin/llama-b10978/llama-server", worker)
    for path in (
        "data/llama.cpp/b10978/cuda12.8/runtime/libcudart.so.12",
        "models/Qwen3-4B-Instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
    ):
        target = project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    env = os.environ.copy()
    for key in ("LLAMA_HOST", "LLAMA_PORT", "LINGUAFORGE_LLAMA_LOG"):
        env.pop(key, None)
    env.update(
        PATH=f"{fake_bin}:{env['PATH']}",
        FAKE_STATE=str(state),
        NVM_DIR=str(tmp_path / "no-nvm"),
        LINGUAFORGE_STARTUP_TIMEOUT="2",
    )
    processes = []

    def start(**overrides):
        process = subprocess.Popen(
            ["bash", str(project / "scripts/start_linguaforge.sh")],
            env={**env, **overrides},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append(process)
        return process

    yield project, state, start

    # Mesmo uma asserção falha não deve deixar processos de teste vivos.
    for process in processes:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=10)
    for pid_file in state.glob("*.pid"):
        try:
            os.kill(int(pid_file.read_text()), signal.SIGKILL)
        except ProcessLookupError:
            pass


def _wait_for(path: Path, process: subprocess.Popen, timeout: float = 8) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        if process.poll() is not None:
            pytest.fail(f"Launcher encerrou antes de {path.name}: {process.communicate()[0]}")
        time.sleep(0.05)
    pytest.fail(f"Launcher não criou {path.name} no prazo esperado.")


def _assert_processes_stopped(state: Path) -> None:
    for pid_file in state.glob("*.pid"):
        status_path = Path("/proc") / pid_file.read_text() / "stat"
        if status_path.exists():
            assert status_path.read_text().split(") ", 1)[1][0] == "Z", pid_file.name


def _wait_for_ready_output(process: subprocess.Popen) -> str:
    output = ""
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if select.select([process.stdout], [], [], 0.1)[0]:
            chunk = os.read(process.stdout.fileno(), 4096).decode()
            output += chunk
            if "LinguaForge disponível" in output:
                return output
            if not chunk:
                break
    pytest.fail(f"A aplicação não anunciou readiness: {output}")


def test_startup_waits_for_app_and_terminates_process_groups(launcher):
    _, state, start = launcher
    process = start(FAKE_STUBBORN="app")
    _wait_for(state / "app", process)
    output = _wait_for_ready_output(process)
    process.terminate()
    output += process.communicate(timeout=10)[0]
    calls = (state / "curl.jsonl").read_text().splitlines()
    assert process.returncode == 143
    assert "LinguaForge disponível" in output
    _assert_processes_stopped(state)
    uv_args = json.loads((state / "app.args").read_text())
    assert uv_args == ["run", "--no-sync", "--offline", "--no-python-downloads", "linguaforge-web"]
    for line in calls:
        args = json.loads(line)
        assert args[args.index("--max-time") + 1] == "2"
        assert args[args.index("--connect-timeout") + 1] == "1"


def test_existing_model_is_reused_without_starting_or_stopping_it(launcher):
    _, state, start = launcher
    process = start(FAKE_EXISTING_LLAMA="1")
    _wait_for(state / "app", process)
    process.send_signal(signal.SIGINT)
    output = process.communicate(timeout=10)[0]
    assert process.returncode == 130
    assert "Usando llama-server já em execução" in output
    assert not (state / "llama.pid").exists()
    _assert_processes_stopped(state)


@pytest.mark.parametrize("component", ["llama", "app"])
def test_startup_failure_cleans_owned_processes(launcher, component):
    _, state, start = launcher
    process = start(FAKE_FAIL=component)
    output = process.communicate(timeout=12)[0]
    assert process.returncode == 1
    assert "LinguaForge disponível" not in output
    _assert_processes_stopped(state)


def test_unready_app_times_out_and_cleans_up(launcher):
    _, state, start = launcher
    process = start(FAKE_APP_UNREADY="1")
    output = process.communicate(timeout=12)[0]
    assert process.returncode == 1
    assert "A aplicação não ficou disponível" in output
    assert "LinguaForge disponível" not in output
    _assert_processes_stopped(state)


def test_invalid_health_body_is_not_readiness(launcher):
    _, state, start = launcher
    process = start(FAKE_BAD_HEALTH="1")
    output = process.communicate(timeout=12)[0]
    assert process.returncode == 1
    assert "O modelo não ficou disponível" in output
    assert not (state / "app.pid").exists()
    _assert_processes_stopped(state)


@pytest.mark.parametrize("name,value", [("LLAMA_HOST", "0.0.0.0"), ("LLAMA_PORT", "9999")])
def test_custom_model_endpoint_is_rejected_before_launch(launcher, name, value):
    _, state, start = launcher
    process = start(**{name: value})
    output = process.communicate(timeout=5)[0]
    assert process.returncode == 1
    assert "127.0.0.1:8080" in output
    assert not tuple(state.glob("*.pid"))


def test_missing_frontend_dependency_fails_before_loading_model(launcher):
    project, state, start = launcher
    (project / "frontend/node_modules/.bin/vite").unlink()
    process = start()
    output = process.communicate(timeout=5)[0]
    assert process.returncode == 1
    assert "Dependência local ausente" in output
    assert not tuple(state.glob("*.pid"))


def test_existing_app_is_left_running(launcher):
    _, state, start = launcher
    process = start(FAKE_EXISTING_APP="1", FAKE_EXISTING_LLAMA="1")
    output = process.communicate(timeout=5)[0]
    assert process.returncode == 0
    assert "já está em execução" in output
    assert not tuple(state.glob("*.pid"))


def test_other_service_on_app_port_is_left_untouched(launcher):
    _, state, start = launcher
    process = start(FAKE_OCCUPIED="1")
    output = process.communicate(timeout=5)[0]
    assert process.returncode == 1
    assert "porta 8000 está ocupada" in output
    assert not tuple(state.glob("*.pid"))


def test_build_failure_stops_the_model_without_announcing_readiness(launcher):
    _, state, start = launcher
    process = start(FAKE_BUILD_FAIL="1")
    output = process.communicate(timeout=10)[0]
    assert process.returncode == 1
    assert "LinguaForge disponível" not in output
    assert (state / "llama.pid").exists()
    assert not (state / "app.pid").exists()
    _assert_processes_stopped(state)


def test_model_failure_after_readiness_stops_application(launcher):
    _, state, start = launcher
    process = start()
    output = _wait_for_ready_output(process)
    os.kill(int((state / "llama.pid").read_text()), signal.SIGTERM)
    output += process.communicate(timeout=10)[0]
    assert process.returncode != 0
    assert "O llama-server encerrou" in output
    _assert_processes_stopped(state)


def test_unsupported_node_fails_before_loading_model(launcher):
    project, state, start = launcher
    _executable(project.parent / "bin/node", "#!/bin/sh\nexit 1\n")
    process = start()
    output = process.communicate(timeout=5)[0]
    assert process.returncode == 1
    assert "Node.js compatível não encontrado" in output
    assert not tuple(state.glob("*.pid"))


def test_running_app_without_model_starts_model_and_preserves_app(launcher):
    _, state, start = launcher
    process = start(FAKE_EXISTING_APP="1")
    output = _wait_for_ready_output(process)
    assert (state / "llama.pid").exists()
    assert not (state / "app.pid").exists()
    process.terminate()
    output += process.communicate(timeout=10)[0]
    assert process.returncode == 143
    _assert_processes_stopped(state)
