import subprocess
from typing import Sequence


def run_command(
    command: Sequence[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"Exit code: {result.returncode}"
        raise RuntimeError(f"Command failed: {' '.join(command)} | {details}")

    return result