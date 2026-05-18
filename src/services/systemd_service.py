from __future__ import annotations

from dataclasses import dataclass

from utils.process_utils import run_command, which_required


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


@dataclass(slots=True, kw_only=True)
class SystemdScheduleParams:
    """Parameter object for scheduling a transient systemd unit."""

    unit_name: str
    command: list[str]
    delay_seconds: int
    is_user_unit: bool
    description: str | None = None


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

    _ERR_UNIT_NAME_EMPTY = "unit_name cannot be empty."
    _ERR_COMMAND_EMPTY = "command cannot be empty."
    _ERR_COMMAND_BLANK_PART = "command cannot contain empty parts."
    _ERR_DELAY_NOT_POSITIVE = "delay_seconds must be greater than zero."

    def schedule(self, params: SystemdScheduleParams) -> SystemdScheduleResult:
        schedule_command = self.build_schedule_command(params)

        result = run_command(schedule_command)

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if self._has_polkit_error(stderr):
            return SystemdScheduleResult(
                success=False,
                message=(
                    f"Scheduled unit {params.unit_name}, but it may fail due to "
                    "missing privileges. System actions (suspend/hibernate/power off) "
                    "require passwordless polkit rules or a graphical session."
                ),
                unit_name=params.unit_name,
                is_user_unit=params.is_user_unit,
                command=schedule_command,
                stdout=stdout,
                stderr=stderr,
            )

        return SystemdScheduleResult(
            success=True,
            message=f"Scheduled transient unit: {params.unit_name}",
            unit_name=params.unit_name,
            is_user_unit=params.is_user_unit,
            command=schedule_command,
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _has_polkit_error(stderr: str) -> bool:
        lowered = stderr.lower()
        return "polkit" in lowered or "authentication" in lowered

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

        messages = self._run_cancel_steps(base_command, timer_unit, service_unit)

        if messages:
            detail = " | ".join(messages)
            return SystemdCancelResult(
                success=False,
                message=f"Cancellation had issues for unit: {unit_name} — {detail}",
                unit_name=unit_name,
                is_user_unit=is_user_unit,
            )

        return SystemdCancelResult(
            success=True,
            message=f"Cancelled scheduled action for unit: {unit_name}",
            unit_name=unit_name,
            is_user_unit=is_user_unit,
        )

    def build_schedule_command(self, params: SystemdScheduleParams) -> list[str]:
        self._validate_unit_name(params.unit_name)
        self._validate_command(params.command)
        self._validate_delay_seconds(params.delay_seconds)

        systemd_run_path = which_required("systemd-run")

        cmd: list[str] = [systemd_run_path]

        if params.is_user_unit:
            cmd.append("--user")

        cmd.extend(
            [
                "--no-block",
                "--unit",
                params.unit_name,
                "--on-active",
                f"{params.delay_seconds}s",
                f"--timer-property=AccuracySec={self.TIMER_ACCURACY}",
                "--collect",
                "--property=Type=oneshot",
            ]
        )

        if params.description and params.description.strip():
            cmd.extend(["--description", params.description.strip()])

        cmd.extend(params.command)
        return cmd

    def _run_cancel_steps(
        self,
        base_command: list[str],
        timer_unit: str,
        service_unit: str,
    ) -> list[str]:
        messages: list[str] = []

        for args in (
            [*base_command, "stop", timer_unit],
            [*base_command, "stop", service_unit],
            [*base_command, "reset-failed", timer_unit],
            [*base_command, "reset-failed", service_unit],
        ):
            result = run_command(args, check=False)
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                if stderr and "not loaded" not in stderr.lower():
                    messages.append(stderr)

        return messages

    def _build_systemctl_base(self, is_user_unit: bool) -> list[str]:
        systemctl_path = which_required("systemctl")
        base = [systemctl_path]

        if is_user_unit:
            base.append("--user")

        return base

    @staticmethod
    def _validate_unit_name(unit_name: str) -> None:
        if not unit_name or not unit_name.strip():
            raise ValueError(SystemdService._ERR_UNIT_NAME_EMPTY)

    @staticmethod
    def _validate_command(command: list[str]) -> None:
        if not command:
            raise ValueError(SystemdService._ERR_COMMAND_EMPTY)

        if any(not str(part).strip() for part in command):
            raise ValueError(SystemdService._ERR_COMMAND_BLANK_PART)

    @staticmethod
    def _validate_delay_seconds(delay_seconds: int) -> None:
        if delay_seconds <= 0:
            raise ValueError(SystemdService._ERR_DELAY_NOT_POSITIVE)
