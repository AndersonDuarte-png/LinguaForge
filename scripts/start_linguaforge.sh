#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
llama_url="http://127.0.0.1:8080/health"
app_url="http://127.0.0.1:8000"
llama_log="${LINGUAFORGE_LLAMA_LOG:-$project_dir/data/llama-server.log}"
startup_timeout="${LINGUAFORGE_STARTUP_TIMEOUT:-120}"
llama_pid=""
app_pid=""
app_already_running=false

cleanup() {
    local pid deadline
    trap '' INT TERM
    for pid in "$app_pid" "$llama_pid"; do
        [[ -z "$pid" ]] || kill -TERM -- "-$pid" 2>/dev/null || true
    done
    deadline=$((SECONDS + 5))
    for pid in "$app_pid" "$llama_pid"; do
        [[ -n "$pid" ]] || continue
        while kill -0 -- "-$pid" 2>/dev/null && ((SECONDS < deadline)); do
            sleep 0.1
        done
        kill -KILL -- "-$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    done
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ! "$startup_timeout" =~ ^[1-9][0-9]*$ ]]; then
    printf 'LINGUAFORGE_STARTUP_TIMEOUT deve ser um número inteiro positivo.\n' >&2
    exit 1
fi
for command in curl setsid; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Comando necessário não encontrado: %s\n' "$command" >&2
        exit 1
    fi
done

# Confere os componentes instalados antes de reservar memória para o modelo.
"$project_dir/scripts/start_app.sh" --check
project_python="$project_dir/.venv/bin/python"

is_ready() {
    local response
    response="$(curl --noproxy '*' --fail --silent --connect-timeout 1 --max-time 2 --max-filesize 8192 "$1")" || return 1
    "$project_python" -c 'import json, sys
try:
    payload = json.loads(sys.argv[1])
    sys.exit(0 if isinstance(payload, dict) and payload.get("status") == "ok" else 1)
except (ValueError, TypeError):
    sys.exit(1)' "$response"
}

wait_until_ready() {
    local url="$1" pid="$2" description="$3" deadline=$((SECONDS + startup_timeout))
    while ((SECONDS < deadline)); do
        if ! kill -0 "$pid" 2>/dev/null; then
            printf '%s encerrou antes de ficar disponível.\n' "$description" >&2
            return 1
        fi
        if [[ -n "$llama_pid" ]] && ! kill -0 "$llama_pid" 2>/dev/null; then
            printf 'O llama-server encerrou. Consulte: %s\n' "$llama_log" >&2
            return 1
        fi
        if is_ready "$url" && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.2
    done
    printf '%s não ficou disponível em %s segundos.\n' "$description" "$startup_timeout" >&2
    return 1
}

if is_ready "$app_url/api/health"; then
    app_already_running=true
fi

# Um serviço diferente na porta da aplicação deve permanecer intocado.
if [[ "$app_already_running" == false ]]; then
"$project_python" -c 'import socket, sys
try:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 8000))
except OSError:
    sys.exit("A porta 8000 está ocupada. Encerre a instância anterior antes de iniciar LinguaForge.")'
fi

if is_ready "$llama_url"; then
    printf 'Usando llama-server já em execução em %s.\n' "$llama_url"
else
    mkdir -p -- "$(dirname -- "$llama_log")"
    printf 'Iniciando llama-server (log: %s)...\n' "$llama_log"
    setsid "$project_dir/scripts/start_llama_server.sh" >"$llama_log" 2>&1 &
    llama_pid=$!
    if ! wait_until_ready "$llama_url" "$llama_pid" 'O modelo'; then
        printf 'Consulte o log: %s\n' "$llama_log" >&2
        exit 1
    fi
fi

# Grupos separados permitem encerrar também os filhos de npm e uv.
if [[ "$app_already_running" == false ]]; then
    setsid "$project_dir/scripts/start_app.sh" &
    app_pid=$!
    wait_until_ready "$app_url/api/health" "$app_pid" 'A aplicação' || exit 1
else
    printf 'LinguaForge já está em execução em %s.\n' "$app_url"
    if [[ -z "$llama_pid" ]]; then
        exit 0
    fi
fi
printf 'LinguaForge disponível em %s\n' "$app_url"
printf 'Use Ctrl+C para encerrar a aplicação e o modelo iniciado por este script.\n'

exit_status=0
if [[ -n "$llama_pid" ]]; then
    owned_pids=("$llama_pid")
    [[ -z "$app_pid" ]] || owned_pids+=("$app_pid")
    wait -n "${owned_pids[@]}" || exit_status=$?
    if ! kill -0 "$llama_pid" 2>/dev/null; then
        printf 'O llama-server encerrou. Consulte: %s\n' "$llama_log" >&2
        ((exit_status != 0)) || exit_status=1
    fi
else
    wait "$app_pid" || exit_status=$?
fi
exit "$exit_status"
