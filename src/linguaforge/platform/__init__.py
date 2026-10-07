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

__all__ = [
    "FileLock",
    "LockNotAvailable",
    "UserDirs",
    "resolve_user_dirs",
    "webview_gui",
]
