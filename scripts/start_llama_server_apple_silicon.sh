#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="$ROOT_DIR/config/models.yaml"
CONFIG_HELPER="$SCRIPT_DIR/llama_server_config.py"
printf -v QUOTED_ROOT_DIR '%q' "$ROOT_DIR"
SETUP_COMMAND="cd $QUOTED_ROOT_DIR && python3 -m venv .venv && "
SETUP_COMMAND+=".venv/bin/python -m pip install -r requirements-dev.txt"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  printf '%s\n' "Error: llama-server requires macOS on Apple Silicon." >&2
  exit 1
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  printf '%s\n' "Error: Python 3 is required. Install it with: brew install python" >&2
  printf 'Then set up the project with: %s\n' "$SETUP_COMMAND" >&2
  exit 1
fi

if ! "$PYTHON" -c "import yaml" >/dev/null 2>&1; then
  printf 'Error: PyYAML is required. Run: %s\n' "$SETUP_COMMAND" >&2
  exit 1
fi

if ! command -v llama-server >/dev/null 2>&1; then
  printf '%s\n' \
    "Error: llama-server was not found. Install it with: brew install llama.cpp" >&2
  exit 1
fi

set +e
assignments="$("$PYTHON" "$CONFIG_HELPER" shell --config "$CONFIG_PATH")"
config_status=$?
set -e
if ((config_status != 0)); then
  exit "$config_status"
fi
eval "$assignments"

if [[ ! -r "$LLAMA_MODEL_PATH" ]]; then
  printf 'Error: model file is not readable: %s\n' "$LLAMA_MODEL_PATH" >&2
  exit 1
fi

if [[ ! -r "$LLAMA_MMPROJ_PATH" ]]; then
  printf 'Error: vision projector file is not readable: %s\n' "$LLAMA_MMPROJ_PATH" >&2
  exit 1
fi

command=(
  llama-server
  -m "$LLAMA_MODEL_PATH"
  --mmproj "$LLAMA_MMPROJ_PATH"
  --host "$LLAMA_HOST"
  --port "$LLAMA_PORT"
  --ctx-size "$LLAMA_CTX_SIZE"
  -ngl "$LLAMA_GPU_LAYERS"
  --log-format text
)

display_host="$LLAMA_HOST"
if [[ "$display_host" == *:* && "$display_host" != \[*\] ]]; then
  display_host="[$display_host]"
fi

printf 'Endpoint: http://%s:%s/v1\n' "$display_host" "$LLAMA_PORT"
printf 'Command:'
printf ' %q' "${command[@]}"
printf '\n'

if [[ "${LLAMA_DRY_RUN:-0}" == "1" ]]; then
  exit 0
fi

exec "${command[@]}"
