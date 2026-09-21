"""Verifica o bundle fora do checkout, com dados temporários e sem iniciar o modelo."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
from tempfile import TemporaryDirectory
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--window", action="store_true")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="linguaforge-bundle-test-") as directory:
        root = Path(directory)
        bundle = root / "bundle"
        shutil.copytree(args.bundle.resolve(), bundle)
        executable = bundle / "linguaforge-preview"
        environment = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
            environment.pop(key, None)
        # O programa não pode depender de Python, Node ou uv disponíveis no PATH.
        environment["PATH"] = str(root / "empty-path")
        for key, folder in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state"), ("XDG_CACHE_HOME", "cache")):
            environment[key] = str(root / folder)
        result = subprocess.run([str(executable), "--check"], cwd=root, env=environment, text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stderr)
        paths = json.loads(result.stdout)
        assert Path(paths["frontend_dir"]).is_relative_to(bundle)
        assert Path(paths["data_dir"]) == root / "data/linguaforge"
        assert not (root / "data").exists(), "--check must not create user data"
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        base = f"http://127.0.0.1:{port}"

        def request(path: str, method: str = "GET", payload=None):
            data = None if payload is None else json.dumps(payload).encode()
            with urlopen(Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"}), timeout=3) as response:
                return response.read()

        @contextmanager
        def api():
            with (root / "api.log").open("a+") as log:
                process = subprocess.Popen([str(executable), "--serve-only", "--port", str(port)], cwd=root, env=environment, stdout=log, stderr=log)
                try:
                    for _ in range(100):
                        if process.poll() is not None:
                            log.seek(0)
                            raise RuntimeError(log.read())
                        try:
                            assert json.loads(request("/api/health")) == {"status": "ok"}
                            break
                        except (URLError, TimeoutError):
                            time.sleep(0.1)
                    else:
                        raise RuntimeError("Packaged API did not become available.")
                    yield
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        raise

        with api():
            html = request("/").decode()
            assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
            assert assets
            for asset in assets:
                assert request(asset)
            chat = json.loads(request("/api/chats", "POST"))
            request(f"/api/chats/{chat['id']}", "PATCH", {"title": "Packaged history"})
        with api():
            chats = json.loads(request("/api/chats"))
            assert len(chats) == 1 and chats[0]["title"] == "Packaged history"
            request(f"/api/chats/{chat['id']}", "DELETE")
            assert json.loads(request("/api/chats")) == []
        print("PASS: relocated bundle, empty PATH, static assets, API and history after restart.", flush=True)
        if args.window:
            for opening in range(2):
                result = subprocess.run([str(executable), "--smoke-test", "--no-model", "--port", str(port)], cwd=root, env=environment, text=True, capture_output=True, timeout=60)
                print(result.stdout, end="", flush=True)
                if result.returncode:
                    raise RuntimeError(result.stderr)
                assert "Desktop smoke test passed" in result.stdout
                if opening == 1:
                    assert "WebView storage restored: true" in result.stdout
        assert not (bundle / "data").exists()


if __name__ == "__main__":
    main()
