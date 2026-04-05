#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
TMP_CONFIG_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_CONFIG_DIR"
}

trap cleanup EXIT INT TERM

mkdir -p "$TMP_CONFIG_DIR/gtk-4.0"

cd "$PROJECT_DIR"

echo "[run-dev] Launching Power Scheduler with isolated GTK config"
echo "[run-dev] Temporary XDG_CONFIG_HOME: $TMP_CONFIG_DIR"

XDG_CONFIG_HOME="$TMP_CONFIG_DIR" \
PYTHONPATH=src \
"$PYTHON_BIN" src/main.py "$@"