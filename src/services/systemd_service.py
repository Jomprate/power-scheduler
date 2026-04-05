from __future__ import annotations

from dataclasses import dataclass
import shutil

from utils.process_utils import run_command


@dataclass(slots=True)
class SystemdScheduleResult:
    success: bool
    message: str
    unit_name: str
    is_user_unit: bool
    command: list[str]
    stdout: str = ""
    stderr: str = ""


@dataclass(slots=True)
class SystemdCancelResult:
    success: bool
    message: str
    unit_name: str
    is_user_unit: bool


class SystemdService:
    """
    Handles only transient scheduling/cancellation through systemd.

    Responsibility:
    - build and execute `systemd-run` commands
    - cancel transient units with `systemctl`

    It does NOT:
    - decide which action should be executed
    - know about lock/log out/suspend/hibernate/power off semantics
    """

    TIMER_ACCURACY = "1us"

    def schedule(
        self,
        *,
        unit_name: str,
        command: list[str],
        delay_seconds: int,
        is_user_unit: bool,
        description: str | None = None,
    ) -> SystemdScheduleResult:
        if not unit_name.strip():
            raise ValueError("unit_name cannot be empty.")

        if not command:
            raise ValueError("command cannot be empty.")

        if delay_seconds <= 0:
            raise ValueError("delay_seconds must be greater than zero.")

        schedule_command = self.build_schedule_command(
            unit_name=unit_name,
            command=command,
            delay_seconds=delay_seconds,
            is_user_unit=is_user_unit,
            description=description,
        )

        result = run_command(schedule_command)

        return SystemdScheduleResult(
            success=True,
            message=f"Scheduled transient unit: {unit_name}",
            unit_name=unit_name,
            is_user_unit=is_user_unit,
            command=schedule_command,
            stdout=(result.stdout or "").strip(),
            stderr=(result.stderr or "").strip(),
        )

    def cancel(
        self,
        *,
        unit_name: str,
        is_user_unit: bool,
    ) -> SystemdCancelResult:
        if not unit_name.strip():
            raise ValueError("unit_name cannot be empty.")

        base_command = self._build_systemctl_base(is_user_unit)

        run_command([*base_command, "stop", f"{unit_name}.timer"], check=False)
        run_command([*base_command, "stop", f"{unit_name}.service"], check=False)
        run_command([*base_command, "reset-failed", f"{unit_name}.timer"], check=False)
        run_command([*base_command, "reset-failed", f"{unit_name}.service"], check=False)

        return SystemdCancelResult(
            success=True,
            message=f"Cancelled scheduled action for unit: {unit_name}",
            unit_name=unit_name,
            is_user_unit=is_user_unit,
        )

    def build_schedule_command(
        self,
        *,
        unit_name: str,
        command: list[str],
        delay_seconds: int,
        is_user_unit: bool,
        description: str | None = None,
    ) -> list[str]:
        systemd_run_path = self._which_required("systemd-run")

        cmd: list[str] = [systemd_run_path]

        if is_user_unit:
            cmd.append("--user")

        cmd.extend(
            [
                "--no-block",
                "--unit",
                unit_name,
                "--on-active",
                f"{delay_seconds}s",
                f"--timer-property=AccuracySec={self.TIMER_ACCURACY}",
                "--collect",
                "--property=Type=oneshot",
            ]
        )

        if description:
            cmd.extend(["--description", description])

        cmd.extend(command)
        return cmd

    def _build_systemctl_base(self, is_user_unit: bool) -> list[str]:
        systemctl_path = self._which_required("systemctl")
        base = [systemctl_path]

        if is_user_unit:
            base.append("--user")

        return base

    @staticmethod
    def _which_required(binary_name: str) -> str:
        resolved = shutil.which(binary_name)
        if not resolved:
            raise RuntimeError(f"Required binary not found: {binary_name}")
        return resolved