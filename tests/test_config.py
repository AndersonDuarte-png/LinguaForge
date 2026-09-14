from pathlib import Path

from linguaforge import config


def test_config_paths_and_defaults():
    cfg = config.config

    assert isinstance(cfg.project_root, Path)
    assert isinstance(cfg.data_dir, Path)
    assert isinstance(cfg.models_dir, Path)
    assert cfg.project_root == Path(__file__).resolve().parents[1]

    # data_dir and models_dir should be subpaths of project_root
    assert cfg.data_dir == cfg.project_root / "data"
    assert cfg.models_dir == cfg.project_root / "models"

    # Defaults
    assert cfg.device == "auto"
    assert cfg.interface_language == "pt-BR"
    assert cfg.target_language == "en"


def test_config_paths_are_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cfg = config.get_config()

    assert cfg.project_root == Path(__file__).resolve().parents[1]
    assert cfg.data_dir == cfg.project_root / "data"
    assert cfg.models_dir == cfg.project_root / "models"
