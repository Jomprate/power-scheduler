from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Sequence


def run_command(
    command: Sequence[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"Exit code: {result.returncode}"
        raise RuntimeError(f"Command failed: {shlex.join(command)} | {details}")

    return result


def which_required(binary_name: str) -> str:
    resolved = shutil.which(binary_name)
    if not resolved:
        raise RuntimeError(f"Required binary not found: {binary_name}")
    return resolved


def which_optional(binary_name: str) -> str | None:
    return shutil.which(binary_name) or None
