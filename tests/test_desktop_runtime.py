from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import socket

import pytest

from linguaforge.config import get_config
from linguaforge.desktop_app import _SetupBridge, resources_are_ready
from linguaforge.desktop_runtime import DesktopStartupError, InstanceLock, start_or_reuse_model


def test_instance_lock_rejects_second_process_in_same_session(tmp_path):
    first = InstanceLock(tmp_path)
    with first:
        with pytest.raises(DesktopStartupError, match="already running"):
            with InstanceLock(tmp_path):
                pass


def test_existing_healthy_model_is_reused_without_validating_files(monkeypatch, tmp_path):
    monkeypatch.setattr("linguaforge.desktop_runtime.is_healthy", lambda *_args, **_kwargs: True)
    model = start_or_reuse_model(get_config(installed=False), timeout=0.1)
    assert not model.owned
    model.close()


def test_missing_model_fails_before_starting_process(monkeypatch, tmp_path):
    monkeypatch.setattr("linguaforge.desktop_runtime.is_healthy", lambda *_args, **_kwargs: False)
    config = replace(get_config(installed=False), model_path=tmp_path / "missing.gguf")
    with pytest.raises(DesktopStartupError, match="Arquivo necessário"):
        start_or_reuse_model(config, timeout=0.1)


def test_resources_are_ready_requires_existing_model_and_server(tmp_path):
    config = replace(
        get_config(installed=False),
        model_path=tmp_path / "model.gguf",
        llama_server_path=tmp_path / "llama-server",
    )
    assert not resources_are_ready(config)
    config.model_path.touch()
    assert not resources_are_ready(config)
    config.llama_server_path.touch()
    assert resources_are_ready(config)
    invalid_server = config.llama_server_path.with_name("libllama-server-impl.so")
    config = replace(config, llama_server_path=invalid_server)
    invalid_server.touch()
    assert not resources_are_ready(config)


def test_first_run_setup_saves_resources_and_starts_without_reopening(tmp_path, monkeypatch):
    model = tmp_path / "model.gguf"
    server = tmp_path / "llama-server"
    runtime = tmp_path / "runtime"
    model.touch()
    server.touch()
    server.chmod(0o755)
    runtime.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    config = get_config(installed=True)
    started = []

    class Window:
        def load_html(self, page):
            self.page = page

    reopened = []
    bridge = _SetupBridge(config, object(), started.append, lambda: reopened.append(True))
    bridge.window = Window()
    result = bridge.save_resources(str(model), str(server), str(runtime))

    assert result == {"ok": True}
    assert bridge.window.page == "<!doctype html><title>LinguaForge</title><body style='font:16px sans-serif;background:#171923;color:#eee;padding:3rem'><h1>LinguaForge</h1><p>Starting the local tutor…</p></body>"
    assert started[0].model_path == model
    assert started[0].llama_server_path == server
    assert bridge.open_setup() == {"ok": True}
    assert reopened == [True]


def test_started_model_is_terminated_by_the_session(tmp_path):
    script = tmp_path / "fake-server.py"
    script.write_text(
        """#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
Path(__file__).with_name('arguments.txt').write_text(' '.join(sys.argv[1:]))
parser = argparse.ArgumentParser(); parser.add_argument('--port')
arguments, _ = parser.parse_known_args()
port = int(arguments.port)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{\\\"status\\\":\\\"ok\\\"}')
    def log_message(self, *_args): pass
HTTPServer(('127.0.0.1', port), Handler).serve_forever()
"""
    )
    script.chmod(0o755)
    model_path = tmp_path / "model.gguf"
    model_path.touch()
    config = replace(
        get_config(installed=False),
        llama_server_path=Path("/unused"),
        model_path=model_path,
        cuda_runtime_dir=tmp_path / "runtime",
        state_dir=tmp_path / "state",
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = replace(config, llama_server_path=script)
    managed = start_or_reuse_model(config, port=port, timeout=2)
    assert managed.owned
    assert managed.process is not None and managed.process.poll() is None
    arguments = (tmp_path / "arguments.txt").read_text()
    assert "--ctx-size 4096" in arguments
    assert "--parallel 1" in arguments
    managed.close()
    assert managed.process.poll() is not None
