#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PYTHONPATH="${PROJECT_DIR}/src"
exec python3 "${PROJECT_DIR}/src/main.py"
