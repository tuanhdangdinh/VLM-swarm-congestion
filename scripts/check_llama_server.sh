#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="$ROOT_DIR/config/models.yaml"
CONFIG_HELPER="$SCRIPT_DIR/llama_server_config.py"
printf -v QUOTED_ROOT_DIR '%q' "$ROOT_DIR"
SETUP_COMMAND="cd $QUOTED_ROOT_DIR && python3 -m venv .venv && "
SETUP_COMMAND+=".venv/bin/python -m pip install -r requirements-dev.txt"

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

if ! command -v curl >/dev/null 2>&1; then
  printf '%s\n' "Error: curl is required. Install it with: brew install curl" >&2
  exit 1
fi

set +e
HEALTH_URL="$("$PYTHON" "$CONFIG_HELPER" health-url --config "$CONFIG_PATH")"
config_status=$?
set -e
if ((config_status != 0)); then
  exit "$config_status"
fi

if curl --fail --silent --show-error --max-time 5 "$HEALTH_URL" >/dev/null; then
  printf 'llama-server ready: %s\n' "$HEALTH_URL"
  exit 0
fi

printf 'llama-server not ready: %s\n' "$HEALTH_URL" >&2
exit 1
