# Distribuição onedir Windows: recursos imutáveis no bundle, dados graváveis fora.
from pathlib import Path

root = Path(SPECPATH).parent.parent  # raiz do repositório


def _flat_files(source: Path, dest_dir: str) -> list[tuple[str, str]]:
    """Lista os arquivos do backend flat, excluindo marcadores de provisionamento.

    O segundo elemento de cada entrada de `datas` é um diretório de destino:
    o PyInstaller coloca o arquivo em `dest_dir/<nome-do-arquivo>`.
    """
    return [
        (str(path), dest_dir)
        for path in sorted(source.iterdir())
        if path.is_file() and path.name != ".provisioned"
    ]


datas = [
    # Frontend compilado (recurso da aplicação, servido do resource root).
    (str(root / "frontend" / "dist"), "frontend"),
    # Backends llama.cpp gerenciados: Vulkan primary + CPU fallback.
    *_flat_files(
        root / "data" / "llama.cpp" / "b10978" / "win-vulkan-x64",
        "backends/llama.cpp/b10978/win-vulkan-x64",
    ),
    *_flat_files(
        root / "data" / "llama.cpp" / "b10978" / "win-cpu-x64",
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
