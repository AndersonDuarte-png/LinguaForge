#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
nvm_script="${NVM_DIR:-$HOME/.nvm}/nvm.sh"

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --check ) ]]; then
    printf 'Uso: %s [--check]\n' "$0" >&2
    exit 1
fi
if [[ "${LLAMA_HOST:-127.0.0.1}" != 127.0.0.1 || "${LLAMA_PORT:-8080}" != 8080 ]]; then
    printf 'A aplicação usa o modelo em 127.0.0.1:8080. Remova LLAMA_HOST/LLAMA_PORT personalizados.\n' >&2
    exit 1
fi

node_is_supported() {
    command -v node >/dev/null 2>&1 && node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
process.exit((major === 20 && minor >= 19) || (major === 22 && minor >= 12) || major > 22 ? 0 : 1);
' >/dev/null 2>&1
}

# Reutiliza Node do PATH; nvm é apenas uma alternativa local, sem instalação.
if ! node_is_supported && [[ -f "$nvm_script" ]]; then
    source "$nvm_script"
fi
if ! node_is_supported; then
    printf 'Node.js compatível não encontrado. Use Node 20.19+ ou 22.12+.\n' >&2
    exit 1
fi
for command in npm uv; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Comando necessário não encontrado: %s\n' "$command" >&2
        exit 1
    fi
done
for required_path in "$project_dir/.venv/bin/python" "$project_dir/.venv/bin/linguaforge-web" "$project_dir/frontend/node_modules/.bin/vite"; do
    if [[ ! -x "$required_path" ]]; then
        printf 'Dependência local ausente: %s. Prepare o ambiente antes de iniciar.\n' "$required_path" >&2
        exit 1
    fi
done
"$project_dir/.venv/bin/python" -c 'import fastapi, uvicorn, linguaforge.web'

if [[ "${1:-}" == --check ]]; then
    exit 0
fi

(
    cd "$project_dir/frontend"
    npm run build
)

cd "$project_dir"
# A inicialização nunca sincroniza dependências nem baixa Python.
exec uv run --no-sync --offline --no-python-downloads linguaforge-web
