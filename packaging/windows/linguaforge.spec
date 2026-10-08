# Distribuição onedir Windows: recursos imutáveis no bundle, dados graváveis fora.
from pathlib import Path

root = Path(SPECPATH).parent.parent  # raiz do repositório

datas = [
    # Frontend compilado (recurso da aplicação, servido do resource root).
    (str(root / "frontend" / "dist"), "frontend"),
    # Backends llama.cpp gerenciados: Vulkan primary + CPU fallback.
    (
        str(root / "data" / "llama.cpp" / "b10978" / "win-vulkan-x64"),
        "backends/llama.cpp/b10978/win-vulkan-x64",
    ),
    (
        str(root / "data" / "llama.cpp" / "b10978" / "win-cpu-x64"),
        "backends/llama.cpp/b10978/win-cpu-x64",
    ),
]

analysis = Analysis(
    [str(root / "packaging" / "desktop_entry.py")],
    pathex=[str(root / "src")],
    datas=datas,
    hiddenimports=["webview.platforms.winforms", "clr", "clr_loader"],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "pytest", "tkinter", "pkg_resources", "gi"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="LinguaForge",
    console=False,
)
collection = COLLECT(executable, analysis.binaries, analysis.datas, name="LinguaForge")
