"""Ponto de entrada do executável desktop."""

import os
import sys

from linguaforge.desktop_app import main

# Em modo windowed (console=False) do PyInstaller, stdout/stderr podem ser None.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


if __name__ == "__main__":
    main()
