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


def _error_page(message: str, *, allow_setup: bool = False) -> str:
    action = (
        "<button onclick=\"window.pywebview.api.open_setup()\" style=\"background:#5b5ce2;border:0;border-radius:6px;color:white;cursor:pointer;font:inherit;padding:10px 14px\">Configure local resources</button>"
        if allow_setup
        else "<p>Close this window, correct the local configuration, and try again.</p>"
    )
    return """<!doctype html><title>LinguaForge</title><body style='font:16px sans-serif;background:#171923;color:#eee;padding:3rem'><h1>LinguaForge</h1><p>Could not start the local tutor.</p><pre style='white-space:pre-wrap'>%s</pre>%s</body>""" % (html.escape(message), action)


def _setup_page(config) -> str:
    """Cria a tela inicial sem procurar, copiar ou baixar recursos locais."""
    values = {
        "model": html.escape(str(config.model_path), quote=True),
        "server": html.escape(str(config.llama_server_path), quote=True),
        "runtime": html.escape(str(config.cuda_runtime_dir), quote=True),
    }
    return """<!doctype html>
<html><head><title>LinguaForge setup</title><style>
body { background: #171923; color: #eef0f7; font: 16px sans-serif; margin: 0; }
main { box-sizing: border-box; max-width: 720px; margin: 0 auto; padding: 48px 32px; }
h1 { margin: 0 0 12px; } p { color: #c4c8d6; line-height: 1.5; }
label { display: block; font-weight: 600; margin-top: 24px; }
small { color: #a9afc3; display: block; margin: 6px 0; }
.path { display: flex; gap: 8px; } input { background: #252936; border: 1px solid #42495e; border-radius: 6px; color: #eef0f7; flex: 1; font: inherit; min-width: 0; padding: 10px; }
button { background: #5b5ce2; border: 0; border-radius: 6px; color: white; cursor: pointer; font: inherit; padding: 10px 14px; }
button.secondary { background: #363c4d; } button:disabled { cursor: wait; opacity: .65; }
#save { margin-top: 32px; } #status { color: #ffb4ab; margin-top: 18px; min-height: 24px; white-space: pre-wrap; }
</style></head><body><main>
<h1>Initial setup</h1>
<p>Select the local resources already on this computer. LinguaForge will validate their paths, but will not download, move, or copy files.</p>
<label for="model">Model file</label><small>A GGUF model is required.</small>
<div class="path"><input id="model" value="%(model)s"><button class="secondary" onclick="browse('model')">Browse</button></div>
<label for="server">llama.cpp server</label><small>The executable named <code>llama-server</code> is required.</small>
<div class="path"><input id="server" value="%(server)s"><button class="secondary" onclick="browse('server')">Browse</button></div>
<label for="runtime">CUDA runtime</label><small>Recommended for GPU use. Leave it empty to allow the backend CPU fallback.</small>
<div class="path"><input id="runtime" value="%(runtime)s"><button class="secondary" onclick="browse('runtime')">Browse</button></div>
<button id="save" onclick="save()">Save and start</button><div id="status" role="alert"></div>
</main><script>
function status(message) { document.getElementById('status').textContent = message; }
async function browse(kind) {
  const result = await window.pywebview.api['select_' + kind]();
  if (result) document.getElementById(kind).value = result;
}
async function save() {
  const button = document.getElementById('save'); button.disabled = true; status('Validating local resources…');
  const result = await window.pywebview.api.save_resources(
    document.getElementById('model').value,
    document.getElementById('server').value,
    document.getElementById('runtime').value,
  );
  if (result.ok) { status('Starting the local tutor…'); return; }
  status(result.error); button.disabled = false;
}
</script></body></html>""" % values


def resources_are_ready(config) -> bool:
    """Indica se há arquivos mínimos para iniciar o tutor sem adivinhar caminhos."""
    return (
        config.model_path.is_file()
        and config.llama_server_path.name == "llama-server"
        and config.llama_server_path.is_file()
    )


class _SetupBridge:
    """Expõe à tela inicial somente a seleção e gravação explícitas de caminhos."""

    def __init__(self, config, webview_module, start, open_setup) -> None:
        self.config = config
        self.webview_module = webview_module
        self.start = start
        self.open_setup_callback = open_setup
        self.window = None
        self.started = False

    def _select(self, dialog_type: int, file_types: tuple[str, ...] = ()) -> str | None:
        assert self.window is not None
        selected = self.window.create_file_dialog(dialog_type, allow_multiple=False, file_types=file_types)
        return str(selected[0]) if selected else None

    def select_model(self) -> str | None:
        return self._select(self.webview_module.FileDialog.OPEN, ("GGUF (*.gguf)",))

    def select_server(self) -> str | None:
        return self._select(self.webview_module.FileDialog.OPEN, ("All files (*)",))

    def select_runtime(self) -> str | None:
        return self._select(self.webview_module.FileDialog.FOLDER)

    def open_setup(self) -> dict[str, bool]:
        """Permite corrigir caminhos após uma falha de inicialização."""
        self.started = False
        self.open_setup_callback()
        return {"ok": True}

    def save_resources(self, model: str, server: str, runtime: str) -> dict[str, object]:
        if self.started:
            return {"ok": False, "error": "The local tutor is already starting."}
        if not model.strip() or not server.strip():
            return {"ok": False, "error": "Select both the model file and llama.cpp server."}
        try:
            save_resource_paths(
                self.config.config_dir,
                model_path=Path(model.strip()).expanduser(),
                llama_server_path=Path(server.strip()).expanduser(),
                cuda_runtime_dir=Path(runtime.strip()).expanduser() if runtime.strip() else None,
            )
        except (OSError, ValueError) as error:
            return {"ok": False, "error": str(error)}
        self.started = True
        assert self.window is not None
        self.window.load_html(_LOADING_PAGE)
        self.start(get_config(installed=True))
        return {"ok": True}


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
        needs_setup = not args.no_model and not args.smoke_test and not resources_are_ready(config)
        state: dict[str, object] = {"server": None, "worker": None, "listener": None, "model": None}

        window = None
        setup = None

        def stop_services() -> None:
            """Encerra os serviços desta janela antes de uma nova tentativa."""
            model = state.get("model")
            if isinstance(model, ManagedModel):
                model.close()
            state["model"] = None
            server = state.get("server")
            worker = state.get("worker")
            listener = state.get("listener")
            if isinstance(server, uvicorn.Server):
                server.should_exit = True
            if isinstance(worker, threading.Thread):
                worker.join(timeout=5)
            if isinstance(listener, socket.socket):
                listener.close()
            state.update(server=None, worker=None, listener=None)

        def bootstrap(current_config) -> None:
            try:
                server, worker, listener = _serve_api(current_config, args.port)
                state.update(server=server, worker=worker, listener=listener)
                if not args.no_model:
                    state["model"] = start_or_reuse_model(
                        current_config, timeout=args.model_timeout, on_process=lambda managed: state.update(model=managed)
                    )
                assert window is not None
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
                stop_services()
                if setup is not None:
                    setup.started = False
                window.load_html(_error_page(str(error), allow_setup=True))
                if args.smoke_test:
                    time.sleep(0.2)
                    window.destroy()

        def start_bootstrap(current_config) -> None:
            threading.Thread(target=bootstrap, args=(current_config,), daemon=True).start()

        def show_setup() -> None:
            """Mostra novamente os campos usando os caminhos atualmente salvos."""
            assert window is not None and setup is not None
            stop_services()
            setup.config = get_config(installed=True)
            window.load_html(_setup_page(setup.config))

        setup = _SetupBridge(config, webview, start_bootstrap, show_setup)

        if needs_setup:
            window = webview.create_window(
                "LinguaForge",
                html=_setup_page(config),
                js_api=setup,
                width=760,
                height=720,
                min_size=(360, 500),
                text_select=True,
            )
            setup.window = window
            webview.start(gui="gtk", private_mode=False, storage_path=str(webview_data))
        else:
            window = webview.create_window(
                "LinguaForge",
                html=_LOADING_PAGE,
                js_api=setup,
                width=1050,
                height=760,
                min_size=(360, 500),
                text_select=True,
            )
            webview.start(lambda: start_bootstrap(config), gui="gtk", private_mode=False, storage_path=str(webview_data))
        stop_services()
        error = state.get("error")
        if args.smoke_test and isinstance(error, Exception):
            raise SystemExit(str(error))
    finally:
        lock.__exit__(None, None, None)


if __name__ == "__main__":
    main()
