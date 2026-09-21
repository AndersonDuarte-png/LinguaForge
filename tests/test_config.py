from pathlib import Path

import pytest

from linguaforge import config


def test_config_paths_and_defaults():
    cfg = config.config

    assert isinstance(cfg.project_root, Path)
    assert isinstance(cfg.data_dir, Path)
    assert isinstance(cfg.models_dir, Path)
    assert cfg.project_root == Path(__file__).resolve().parents[1]

    # data_dir e models_dir devem ser subdiretórios de project_root.
    assert cfg.data_dir == cfg.project_root / "data"
    assert cfg.models_dir == cfg.project_root / "models"

    # Valores padrão.
    assert cfg.device == "auto"
    assert cfg.interface_language == "en"
    assert cfg.target_language == "en"


def test_config_paths_are_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cfg = config.get_config()

    assert cfg.project_root == Path(__file__).resolve().parents[1]
    assert cfg.data_dir == cfg.project_root / "data"
    assert cfg.models_dir == cfg.project_root / "models"


def test_installed_paths_use_xdg_and_do_not_create_directories(tmp_path, monkeypatch):
    for variable, folder in [("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state")]:
        monkeypatch.setenv(variable, str(tmp_path / folder))
    cfg = config.get_config(installed=True)
    assert cfg.data_dir == tmp_path / "data/linguaforge"
    assert cfg.config_dir == tmp_path / "config/linguaforge"
    assert cfg.state_dir == tmp_path / "state/linguaforge"
    assert not cfg.data_dir.exists()
    assert cfg.model_path.is_relative_to(cfg.data_dir)
    assert cfg.llama_server_path.is_relative_to(cfg.backend_dir)


def test_frozen_resources_are_separate_from_writable_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config.sys, "_MEIPASS", str(tmp_path / "bundle/_internal"), raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    monkeypatch.chdir(tmp_path)
    cfg = config.get_config()
    assert cfg.frontend_dir == tmp_path / "bundle/_internal/frontend"
    assert cfg.data_dir == tmp_path / "user-data/linguaforge"
    assert not cfg.data_dir.is_relative_to(cfg.project_root)


def test_relative_xdg_is_ignored_and_external_models_can_be_reused(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "relative")
    existing_model = tmp_path / "existing.gguf"
    monkeypatch.setenv("LINGUAFORGE_MODEL_PATH", str(existing_model))
    cfg = config.get_config(installed=True)
    assert cfg.data_dir == Path.home() / ".local/share/linguaforge"
    assert cfg.model_path == existing_model
    assert not existing_model.exists()


def test_development_keeps_legacy_database_and_frontend_paths():
    cfg = config.get_config(installed=False)
    assert cfg.data_dir == cfg.project_root / "data"
    assert cfg.frontend_dir == cfg.project_root / "frontend/dist"
    assert cfg.backend_dir == cfg.data_dir / "llama.cpp/b10978/cuda12.8"


def test_saved_resource_paths_are_used_only_by_installed_application(tmp_path, monkeypatch):
    for variable, folder in [("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state")]:
        monkeypatch.setenv(variable, str(tmp_path / folder))
    model = tmp_path / "source/model.gguf"
    server = tmp_path / "source/llama-server"
    runtime = tmp_path / "source/runtime"
    model.parent.mkdir(parents=True)
    model.touch()
    server.touch()
    server.chmod(0o755)
    runtime.mkdir()
    settings = config.save_resource_paths(
        tmp_path / "config/linguaforge",
        model_path=model,
        llama_server_path=server,
        cuda_runtime_dir=runtime,
    )
    installed = config.get_config(installed=True)
    development = config.get_config(installed=False)
    assert settings.stat().st_mode & 0o777 == 0o600
    assert installed.model_path == model
    assert installed.llama_server_path == server
    assert installed.cuda_runtime_dir == runtime
    assert development.model_path != model


def test_environment_resource_path_has_priority_over_saved_value(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    saved = tmp_path / "saved.gguf"
    override = tmp_path / "override.gguf"
    saved.touch()
    override.touch()
    config.save_resource_paths(tmp_path / "config/linguaforge", model_path=saved)
    monkeypatch.setenv("LINGUAFORGE_MODEL_PATH", str(override))
    assert config.get_config(installed=True).model_path == override


def test_saved_resource_paths_reject_missing_or_relative_values(tmp_path):
    with pytest.raises(ValueError, match="Arquivo não encontrado"):
        config.save_resource_paths(tmp_path, model_path=tmp_path / "missing.gguf")
    with pytest.raises(ValueError, match="absoluto"):
        config.save_resource_paths(tmp_path, llama_server_path=Path("relative-server"))


@pytest.mark.parametrize("variable", ["LINGUAFORGE_MODEL_PATH", "LINGUAFORGE_LLAMA_SERVER", "LINGUAFORGE_CUDA_RUNTIME_DIR"])
def test_relative_external_paths_are_rejected(monkeypatch, variable):
    monkeypatch.setenv(variable, "relative/path")
    with pytest.raises(ValueError, match=variable):
        config.get_config(installed=True)
