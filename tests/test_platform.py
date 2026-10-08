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


def test_linux_valid_server_names():
    assert linux.valid_server_names() == ("llama-server",)


def test_windows_valid_server_names_accept_exe():
    assert "llama-server.exe" in windows.valid_server_names()


def test_linux_development_backend_dir():
    data_dir = Path("/repo/data")
    assert linux.development_backend_dir(data_dir) == data_dir / "llama.cpp" / "b10978" / "cuda12.8"


def test_windows_development_backend_dir():
    data_dir = Path("D:/repo/data")
    assert windows.development_backend_dir(data_dir) == data_dir / "llama.cpp" / "b10978" / "win-vulkan-x64"


def test_windows_cpu_backend_dir_is_preserved():
    data_dir = Path("D:/repo/data")
    assert windows.cpu_backend_dir(data_dir) == data_dir / "llama.cpp" / "b10978" / "win-cpu-x64"


def test_windows_installed_backends_root_is_app_backends():
    project_root = Path("C:/app")
    assert windows.installed_backends_root(project_root, Path("C:/users/x/AppData/Local/LinguaForge")) == project_root / "backends"


def test_linux_installed_backends_root_preserves_data_dir():
    data_dir = Path("/home/u/.local/share/linguaforge")
    assert linux.installed_backends_root(Path("/opt/linguaforge"), data_dir) == data_dir


def test_linux_cpu_backend_dir_matches_cuda_backend():
    data_dir = Path("/repo/data")
    assert linux.cpu_backend_dir(data_dir) == linux.development_backend_dir(data_dir)


def test_linux_default_server_path():
    backend_dir = Path("/repo/data/llama.cpp/b10978/cuda12.8")
    assert linux.default_server_path(backend_dir) == backend_dir / "bin" / "llama-b10978" / "llama-server"


def test_windows_default_server_path():
    backend_dir = Path("D:/repo/data/llama.cpp/b10978/win-cpu-x64")
    assert windows.default_server_path(backend_dir) == backend_dir / "llama-server.exe"


def test_linux_default_gpu_layers_preserves_previous():
    assert linux.default_gpu_layers() == "999"


def test_windows_default_gpu_layers_is_vulkan_full_offload():
    assert windows.default_gpu_layers() == "999"
