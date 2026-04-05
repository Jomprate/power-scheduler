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
        self._validate_unit_name(unit_name)
        self._validate_command(command)
        self._validate_delay_seconds(delay_seconds)

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
        self._validate_unit_name(unit_name)

        base_command = self._build_systemctl_base(is_user_unit)

        timer_unit = f"{unit_name}.timer"
        service_unit = f"{unit_name}.service"

        run_command([*base_command, "stop", timer_unit], check=False)
        run_command([*base_command, "stop", service_unit], check=False)
        run_command([*base_command, "reset-failed", timer_unit], check=False)
        run_command([*base_command, "reset-failed", service_unit], check=False)

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
        self._validate_unit_name(unit_name)
        self._validate_command(command)
        self._validate_delay_seconds(delay_seconds)

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

        if description and description.strip():
            cmd.extend(["--description", description.strip()])

        cmd.extend(command)
        return cmd

    def _build_systemctl_base(self, is_user_unit: bool) -> list[str]:
        systemctl_path = self._which_required("systemctl")
        base = [systemctl_path]

        if is_user_unit:
            base.append("--user")

        return base

    @staticmethod
    def _validate_unit_name(unit_name: str) -> None:
        if not unit_name or not unit_name.strip():
            raise ValueError("unit_name cannot be empty.")

    @staticmethod
    def _validate_command(command: list[str]) -> None:
        if not command:
            raise ValueError("command cannot be empty.")

        if any(not str(part).strip() for part in command):
            raise ValueError("command cannot contain empty parts.")

    @staticmethod
    def _validate_delay_seconds(delay_seconds: int) -> None:
        if delay_seconds <= 0:
            raise ValueError("delay_seconds must be greater than zero.")

    @staticmethod
    def _which_required(binary_name: str) -> str:
        resolved = shutil.which(binary_name)
        if not resolved:
            raise RuntimeError(f"Required binary not found: {binary_name}")
        return resolved