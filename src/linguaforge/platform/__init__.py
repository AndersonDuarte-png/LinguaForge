"""Ponto único de seleção de diferenças entre sistemas operacionais."""

from __future__ import annotations

import sys

from linguaforge.platform._types import LockNotAvailable, ModelBackend, UserDirs

if sys.platform == "win32":
    from linguaforge.platform import windows as _implementation
else:
    from linguaforge.platform import linux as _implementation

resolve_user_dirs = _implementation.resolve_user_dirs
webview_gui = _implementation.webview_gui
FileLock = _implementation.FileLock
prepare_environment = _implementation.prepare_environment
spawn_process = _implementation.spawn_process
terminate_process = _implementation.terminate_process
valid_server_names = _implementation.valid_server_names
development_backend_dir = _implementation.development_backend_dir
cpu_backend_dir = _implementation.cpu_backend_dir
default_server_path = _implementation.default_server_path
default_gpu_layers = _implementation.default_gpu_layers
model_backends = _implementation.model_backends

__all__ = [
    "FileLock",
    "LockNotAvailable",
    "ModelBackend",
    "UserDirs",
    "cpu_backend_dir",
    "default_gpu_layers",
    "default_server_path",
    "development_backend_dir",
    "model_backends",
    "prepare_environment",
    "resolve_user_dirs",
    "spawn_process",
    "terminate_process",
    "valid_server_names",
    "webview_gui",
]
