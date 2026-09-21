#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python="$project_dir/.venv-desktop/bin/python"
if [[ ! -x "$python" ]]; then
    printf 'Prepare .venv-desktop conforme docs/empacotamento-etapa2.md.\n' >&2
    exit 1
fi
# O build usa o Python nativo para acessar os bindings GTK da distribuição.
"$python" -c 'import gi, cairo, webview, PyInstaller; gi.require_version("Gtk", "3.0"); gi.require_version("WebKit2", "4.1"); from gi.repository import Gtk, WebKit2'
if [[ -f "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]]; then
    source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
fi
(
    cd "$project_dir/frontend"
    npm run build
)
cd "$project_dir"
"$python" -m PyInstaller --noconfirm --distpath "$project_dir/dist" --workpath "$project_dir/build/desktop-preview" "$project_dir/packaging/linguaforge-preview.spec"
