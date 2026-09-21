"""Ponto de entrada da aplicação desktop instalada."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import html
import json
from pathlib import Path
import socket
import threading
import time

import uvicorn

from linguaforge.config import get_config, save_resource_paths
from linguaforge.desktop_runtime import DesktopStartupError, InstanceLock, ManagedModel, start_or_reuse_model
from linguaforge.storage_import import import_chat_history
from linguaforge.web import create_app


_LOADING_PAGE = """<!doctype html><title>LinguaForge</title><body style='font:16px sans-serif;background:#171923;color:#eee;padding:3rem'><h1>LinguaForge</h1><p>Starting the local tutor…</p></body>"""


def _error_page(message: str) -> str:
    return """<!doctype html><title>LinguaForge</title><body style='font:16px sans-serif;background:#171923;color:#eee;padding:3rem'><h1>LinguaForge</h1><p>Could not start the local tutor.</p><pre style='white-space:pre-wrap'>%s</pre><p>Close this window, correct the local configuration, and try again.</p></body>""" % html.escape(message)


def _serve_api(config, port: int) -> tuple[uvicorn.Server, threading.Thread, socket.socket]:
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", port))
    except OSError as error:
        listener.close()
        raise DesktopStartupError(f"A porta da aplicação está ocupada: 127.0.0.1:{port}.") from error
    server = uvicorn.Server(uvicorn.Config(create_app(config=config), ws="none", log_level="warning"))
    worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    worker.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if not worker.is_alive() or time.monotonic() >= deadline:
            server.should_exit = True
            worker.join(timeout=3)
            raise DesktopStartupError("A API local não pôde ser iniciada.")
        time.sleep(0.05)
    return server, worker, listener


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LinguaForge desktop application")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--serve-only", action="store_true")
    parser.add_argument("--no-model", action="store_true", help="Open the interface without starting llama-server")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--smoke-hold-seconds", type=float, default=0.0)
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--model-timeout", type=float, default=120.0)
    parser.add_argument("--import-chats", type=Path, metavar="SOURCE")
    parser.add_argument("--configure-resources", action="store_true", help="Save existing local model/backend paths")
    parser.add_argument("--model", type=Path, metavar="PATH")
    parser.add_argument("--server", type=Path, metavar="PATH")
    parser.add_argument("--cuda-runtime", type=Path, metavar="DIRECTORY")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if not 0 <= args.port <= 65535 or args.model_timeout <= 0 or args.smoke_hold_seconds < 0:
        raise SystemExit("Porta inválida ou tempo de inicialização não positivo.")
    if args.smoke_test and args.serve_only:
        raise SystemExit("Smoke test não pode ser combinado com --serve-only.")
    config = get_config(installed=True)
    if args.configure_resources:
        destination = save_resource_paths(
            config.config_dir,
            model_path=args.model,
            llama_server_path=args.server,
            cuda_runtime_dir=args.cuda_runtime,
        )
        print(f"Caminhos locais salvos em: {destination}")
        return
    if not (config.frontend_dir / "index.html").is_file():
        raise SystemExit(f"Frontend compilado não encontrado: {config.frontend_dir}")
    if args.check:
        print(json.dumps({key: str(value) for key, value in asdict(config).items()}, indent=2))
        return
    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.config_dir.mkdir(parents=True, exist_ok=True)
    if args.import_chats:
        backup = import_chat_history(args.import_chats, config.data_dir / "chats.sqlite3")
        print(f"Chat history imported; backup: {backup}", flush=True)
    if args.serve_only:
        server, worker, listener = _serve_api(config, args.port)
        try:
            worker.join()
        finally:
            server.should_exit = True
            worker.join(timeout=5)
            listener.close()
        return

    import webview

    lock = InstanceLock(config.state_dir)
    try:
        lock.__enter__()
    except DesktopStartupError as error:
        webview.create_window("LinguaForge", html=_error_page(str(error)), width=560, height=360)
        webview.start(gui="gtk", private_mode=True)
        return
    try:
        webview_data = config.data_dir / "webview"
        webview_data.mkdir(parents=True, exist_ok=True)
        window = webview.create_window("LinguaForge", html=_LOADING_PAGE, width=1050, height=760, min_size=(360, 500), text_select=True)
        state: dict[str, object] = {"server": None, "worker": None, "listener": None, "model": None}

        def bootstrap() -> None:
            try:
                server, worker, listener = _serve_api(config, args.port)
                state.update(server=server, worker=worker, listener=listener)
                if not args.no_model:
                    state["model"] = start_or_reuse_model(
                        config, timeout=args.model_timeout, on_process=lambda managed: state.update(model=managed)
                    )
                window.load_url(f"http://127.0.0.1:{args.port}")
                if args.smoke_test:
                    for _ in range(100):
                        if window.evaluate_js("Boolean(document.querySelector('.app-shell'))"):
                            restored = window.evaluate_js("localStorage.getItem('linguaforge.packagingSmoke') === 'saved'")
                            window.evaluate_js("localStorage.setItem('linguaforge.packagingSmoke', 'saved')")
                            print(f"WebView storage restored: {str(restored).lower()}", flush=True)
                            print("Desktop smoke test passed: Vue rendered in GTK/WebKit.", flush=True)
                            time.sleep(args.smoke_hold_seconds)
                            window.destroy()
                            return
                        time.sleep(0.1)
                    raise DesktopStartupError("Vue não foi renderizado no prazo do smoke test.")
            except Exception as error:
                state["error"] = error
                window.load_html(_error_page(str(error)))
                if args.smoke_test:
                    time.sleep(0.2)
                    window.destroy()

        webview.start(lambda: threading.Thread(target=bootstrap, daemon=True).start(), gui="gtk", private_mode=False, storage_path=str(webview_data))
        model = state.get("model")
        if isinstance(model, ManagedModel):
            model.close()
        server = state.get("server")
        worker = state.get("worker")
        listener = state.get("listener")
        if isinstance(server, uvicorn.Server):
            server.should_exit = True
        if isinstance(worker, threading.Thread):
            worker.join(timeout=5)
        if isinstance(listener, socket.socket):
            listener.close()
        error = state.get("error")
        if args.smoke_test and isinstance(error, Exception):
            raise SystemExit(str(error))
    finally:
        lock.__exit__(None, None, None)


if __name__ == "__main__":
    main()
