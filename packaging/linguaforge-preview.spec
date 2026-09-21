# Receita inicial: recursos imutáveis no bundle, dados graváveis fora dele.
from pathlib import Path

root = Path(SPECPATH).parent
analysis = Analysis(
    [str(root / "packaging" / "desktop_entry.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "frontend" / "dist"), "frontend")],
    hiddenimports=["webview.platforms.gtk", "gi.repository.Gtk", "gi.repository.WebKit2"],
    # Evita pkg_resources legado da distribuição; dependências atuais usam importlib.metadata.
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "pytest", "tkinter", "pkg_resources"],
    hooksconfig={"gi": {"module-versions": {"Gtk": "3.0", "Gdk": "3.0", "WebKit2": "4.1", "JavaScriptCore": "4.1", "Soup": "3.0"}}},
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True,
    name="linguaforge-preview", console=True,
)
collection = COLLECT(executable, analysis.binaries, analysis.datas, name="linguaforge-preview")
