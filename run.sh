#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_PY="${SCRIPT_DIR}/src/main.py"

if [[ ! -f "${MAIN_PY}" ]]; then
    echo "Error: ${MAIN_PY} not found." >&2
    exit 1
fi

export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
exec python3 "${MAIN_PY}"
