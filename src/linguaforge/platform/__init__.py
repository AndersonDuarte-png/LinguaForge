"""Ponto único de seleção de diferenças entre sistemas operacionais."""

from __future__ import annotations

import sys

from linguaforge.platform._types import LockNotAvailable, UserDirs

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

__all__ = [
    "FileLock",
    "LockNotAvailable",
    "UserDirs",
    "prepare_environment",
    "resolve_user_dirs",
    "spawn_process",
    "terminate_process",
    "webview_gui",
]
