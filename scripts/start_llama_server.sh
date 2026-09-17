#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
server="$project_dir/data/llama.cpp/b10978/cuda12.8/bin/llama-b10978/llama-server"
runtime_dir="$project_dir/data/llama.cpp/b10978/cuda12.8/runtime"
model="$project_dir/models/Qwen3-4B-Instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"

for required_path in "$server" "$runtime_dir/libcudart.so.12" "$model"; do
    if [[ ! -e "$required_path" ]]; then
        printf 'Arquivo necessário não encontrado: %s\n' "$required_path" >&2
        exit 1
    fi
done

export LD_LIBRARY_PATH="$runtime_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$server" \
    --model "$model" \
    --host "${LLAMA_HOST:-127.0.0.1}" \
    --port "${LLAMA_PORT:-8080}" \
    --gpu-layers "${LLAMA_GPU_LAYERS:-999}" \
    "$@"
