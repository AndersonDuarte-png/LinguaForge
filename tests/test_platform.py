"""Testa as implementações de plataforma independentemente do SO do pytest."""

from pathlib import Path

from linguaforge.platform import linux, windows


def test_linux_resolves_xdg_user_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    dirs = linux.resolve_user_dirs()

    assert dirs.data_dir == tmp_path / "data" / "linguaforge"
    assert dirs.config_dir == tmp_path / "config" / "linguaforge"
    assert dirs.state_dir == tmp_path / "state" / "linguaforge"


def test_linux_ignores_relative_xdg_values(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "relative")

    dirs = linux.resolve_user_dirs()

    assert dirs.data_dir == Path.home() / ".local" / "share" / "linguaforge"


def test_linux_webview_gui_is_gtk():
    assert linux.webview_gui() == "gtk"


def test_windows_resolves_native_user_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))

    dirs = windows.resolve_user_dirs()

    assert dirs.data_dir == tmp_path / "local" / "LinguaForge"
    assert dirs.config_dir == tmp_path / "roaming" / "LinguaForge"
    assert dirs.state_dir == tmp_path / "local" / "LinguaForge" / "state"


def test_windows_ignores_relative_appdata_values(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", "relative")
    monkeypatch.setenv("APPDATA", "relative")

    dirs = windows.resolve_user_dirs()

    home = Path.home()
    assert dirs.data_dir == home / "AppData" / "Local" / "LinguaForge"
    assert dirs.config_dir == home / "AppData" / "Roaming" / "LinguaForge"


def test_windows_webview_gui_is_auto():
    assert windows.webview_gui() is None
