"""Prova de execução instalada; gestão do modelo e menu pertencem à próxima etapa."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import socket
import threading
import time

import uvicorn

from linguaforge.config import get_config
from linguaforge.storage_import import import_chat_history
from linguaforge.web import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="LinguaForge desktop packaging preview")
    parser.add_argument("--check", action="store_true", help="Validate packaged resources without starting services")
    parser.add_argument("--serve-only", action="store_true", help="Test the packaged API without opening a window")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--smoke-test", action="store_true", help="Verify the window and close it automatically")
    parser.add_argument("--import-chats", type=Path, metavar="SOURCE", help="Explicitly import existing chats, preserving a backup")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535.")
    if args.smoke_test and args.serve_only:
        parser.error("Smoke test requires a window.")
    cfg = get_config(installed=True)
    if not (cfg.frontend_dir / "index.html").is_file():
        parser.error(f"Compiled frontend is missing: {cfg.frontend_dir}")
    if args.check:
        print(json.dumps({key: str(value) for key, value in asdict(cfg).items()}, indent=2))
        return
    if args.import_chats:
        backup = import_chat_history(args.import_chats, cfg.data_dir / "chats.sqlite3")
        print(f"Chat history imported; backup: {backup}", flush=True)

    if args.serve_only:
        uvicorn.run(create_app(config=cfg), host="127.0.0.1", port=args.port, ws="none")
        return

    import webview

    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    cfg.config_dir.mkdir(parents=True, exist_ok=True)
    webview_data = cfg.data_dir / "webview"
    webview_data.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", args.port))
        server = uvicorn.Server(uvicorn.Config(create_app(config=cfg), ws="none", log_level="warning"))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not worker.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError("The local API could not start.")
                time.sleep(0.05)
            port = listener.getsockname()[1]
            window = webview.create_window("LinguaForge — Desktop preview", f"http://127.0.0.1:{port}", width=1050, height=760, min_size=(360, 500), text_select=True)
            smoke_result = []

            def smoke_check() -> None:
                """Confere Vue montado e encerra somente a janela de teste."""
                try:
                    for _ in range(100):
                        if window.evaluate_js("Boolean(document.querySelector('.app-shell'))"):
                            restored = window.evaluate_js("localStorage.getItem('linguaforge.packagingSmoke') === 'saved'")
                            window.evaluate_js("localStorage.setItem('linguaforge.packagingSmoke', 'saved')")
                            print(f"WebView storage restored: {str(restored).lower()}", flush=True)
                            smoke_result.append(True)
                            print("Desktop smoke test passed: Vue rendered in GTK/WebKit.", flush=True)
                            break
                        time.sleep(0.1)
                finally:
                    window.destroy()

            webview.start(smoke_check if args.smoke_test else None, gui="gtk", private_mode=False, storage_path=str(webview_data))
            if args.smoke_test and not smoke_result:
                raise RuntimeError("Desktop smoke test failed: Vue did not render.")
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            if worker.is_alive():
                raise RuntimeError("The preview API did not stop in time.")


if __name__ == "__main__":
    main()
