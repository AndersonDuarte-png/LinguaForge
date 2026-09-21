"""Caminhos de desenvolvimento e de execução instalada, sem criar diretórios."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Config:
    project_root: Path
    data_dir: Path
    models_dir: Path
    frontend_dir: Path
    config_dir: Path
    state_dir: Path
    backend_dir: Path
    model_path: Path
    llama_server_path: Path
    cuda_runtime_dir: Path
    device: str = "auto"
    interface_language: str = "en"
    target_language: str = "en"


def _xdg_path(name: str, fallback: Path) -> Path:
    """Ignora caminhos XDG relativos, conforme a especificação."""
    value = os.environ.get(name)
    path = Path(value) if value else fallback
    return path if path.is_absolute() else fallback


_RESOURCE_SETTINGS_FILE = "runtime-paths.json"
_RESOURCE_SETTING_NAMES = {
    "LINGUAFORGE_MODEL_PATH": "model_path",
    "LINGUAFORGE_LLAMA_SERVER": "llama_server_path",
    "LINGUAFORGE_CUDA_RUNTIME_DIR": "cuda_runtime_dir",
}


def _saved_resource_paths(config_dir: Path) -> dict[str, str]:
    """Lê apenas caminhos absolutos salvos pela configuração explícita do usuário."""
    try:
        payload = json.loads((config_dir / _RESOURCE_SETTINGS_FILE).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if key in _RESOURCE_SETTING_NAMES.values() and isinstance(value, str) and Path(value).is_absolute()
    }


def _external_path(name: str, fallback: Path, saved: dict[str, str]) -> Path:
    value = os.environ.get(name) or saved.get(_RESOURCE_SETTING_NAMES[name])
    if not value:
        return fallback
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"{name} must be an absolute path.")
    return path


def save_resource_paths(
    config_dir: Path,
    *,
    model_path: Path | None = None,
    llama_server_path: Path | None = None,
    cuda_runtime_dir: Path | None = None,
) -> Path:
    """Salva caminhos locais escolhidos pelo usuário sem copiar modelos ou backend."""
    supplied = {
        "model_path": model_path,
        "llama_server_path": llama_server_path,
        "cuda_runtime_dir": cuda_runtime_dir,
    }
    if not any(path is not None for path in supplied.values()):
        raise ValueError("Informe pelo menos um caminho de recurso.")
    current = _saved_resource_paths(config_dir)
    for key, path in supplied.items():
        if path is None:
            continue
        path = path.expanduser()
        if not path.is_absolute():
            raise ValueError(f"{key} deve ser um caminho absoluto.")
        if key == "cuda_runtime_dir":
            if not path.is_dir():
                raise ValueError(f"Diretório não encontrado: {path}")
        elif not path.is_file():
            raise ValueError(f"Arquivo não encontrado: {path}")
        elif key == "llama_server_path" and not os.access(path, os.X_OK):
            raise ValueError(f"Backend sem permissão de execução: {path}")
        current[key] = str(path)
    config_dir.mkdir(parents=True, exist_ok=True)
    destination = config_dir / _RESOURCE_SETTINGS_FILE
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(current, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    return destination


def get_config(*, installed: bool | None = None) -> Config:
    """Resolve recursos somente de leitura e dados graváveis separadamente."""
    frozen = bool(getattr(sys, "frozen", False))
    if installed is None:
        installed = frozen
    project_root = Path(sys._MEIPASS) if frozen else Path(__file__).resolve().parents[2]
    frontend_dir = project_root / "frontend" if frozen else project_root / "frontend" / "dist"
    if installed:
        home = Path.home()
        data_dir = _xdg_path("XDG_DATA_HOME", home / ".local" / "share") / "linguaforge"
        config_dir = _xdg_path("XDG_CONFIG_HOME", home / ".config") / "linguaforge"
        state_dir = _xdg_path("XDG_STATE_HOME", home / ".local" / "state") / "linguaforge"
        models_dir = data_dir / "models"
        backend_dir = data_dir / "backends" / "llama.cpp"
    else:
        data_dir = project_root / "data"
        models_dir = project_root / "models"
        config_dir = data_dir / "config"
        state_dir = data_dir / "state"
        backend_dir = data_dir / "llama.cpp" / "b10978" / "cuda12.8"

    saved_paths = _saved_resource_paths(config_dir) if installed else {}

    return Config(
        project_root=project_root,
        data_dir=data_dir,
        models_dir=models_dir,
        frontend_dir=frontend_dir,
        config_dir=config_dir,
        state_dir=state_dir,
        backend_dir=backend_dir,
        model_path=_external_path(
            "LINGUAFORGE_MODEL_PATH",
            models_dir / "Qwen3-4B-Instruct-2507" / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
            saved_paths,
        ),
        llama_server_path=_external_path(
            "LINGUAFORGE_LLAMA_SERVER", backend_dir / "bin" / "llama-b10978" / "llama-server", saved_paths
        ),
        cuda_runtime_dir=_external_path("LINGUAFORGE_CUDA_RUNTIME_DIR", backend_dir / "runtime", saved_paths),
    )


# Compatibilidade com consumidores da configuração padrão de desenvolvimento.
config = get_config()
