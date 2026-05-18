from __future__ import annotations

import shlex
from collections.abc import Sequence
from datetime import datetime

from domain.enums import PowerAction
from domain.models import ScheduledJobResult, ScheduleRequest
from repositories.scheduled_job_repository import (
    ScheduledJobRecord,
    ScheduledJobRepository,
)
from services.protocols import PowerActionService
from services.systemd_service import SystemdScheduleParams, SystemdService
from utils.time_utils import format_human_time, to_seconds


class SchedulerService:
    """
    Coordinates scheduling workflow without owning low-level responsibilities.

    Responsibility:
    - validate the schedule request
    - resolve which domain service supports the requested action
    - convert the delay to seconds
    - delegate transient scheduling/cancellation to SystemdService
    - persist the last scheduled job for later recovery/cancellation
    - return a UI-friendly result
    """

    def __init__(
        self,
        *,
        action_services: Sequence[PowerActionService],
        systemd_service: SystemdService,
        scheduled_job_repository: ScheduledJobRepository,
    ) -> None:
        self._action_services = list(action_services)
        self._systemd_service = systemd_service
        self._scheduled_job_repository = scheduled_job_repository

    def schedule(self, request: ScheduleRequest) -> ScheduledJobResult:
        unit_name = self._generate_unit_name(request.action)
        is_user_unit = self._is_user_action(request.action)
        action_command = self._resolve_action_command(request.action)
        delay_seconds = to_seconds(request.amount, request.unit)

        result = self._systemd_service.schedule(
            SystemdScheduleParams(
                unit_name=unit_name,
                command=action_command,
                delay_seconds=delay_seconds,
                is_user_unit=is_user_unit,
                description=f"Power Scheduler: {request.action.value}",
            )
        )

        scheduled_for = format_human_time(request.amount, request.unit)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        message_parts = [
            f"Scheduled {request.action.value} in {scheduled_for}.",
            f"Unit: {unit_name}",
        ]

        if stdout:
            message_parts.append(stdout)

        if stderr:
            message_parts.append(stderr)

        ui_result = ScheduledJobResult(
            success=True,
            message="\n".join(message_parts),
            unit_name=unit_name,
            is_user_unit=is_user_unit,
            command=shlex.join(result.command),
        )

        self._scheduled_job_repository.save_current_job(
            ScheduledJobRecord(
                unit_name=unit_name,
                is_user_unit=is_user_unit,
                action=request.action,
                amount=request.amount,
                unit=request.unit,
                command=ui_result.command,
            )
        )

        return ui_result

    def cancel(self, unit_name: str, is_user_unit: bool) -> ScheduledJobResult:
        result = self._systemd_service.cancel(
            unit_name=unit_name,
            is_user_unit=is_user_unit,
        )

        if result.success:
            stored_job = self._scheduled_job_repository.get_current_job()
            if stored_job is None or stored_job.unit_name == unit_name:
                self._scheduled_job_repository.clear_current_job()

        return ScheduledJobResult(
            success=result.success,
            message=result.message,
            unit_name=result.unit_name,
            is_user_unit=result.is_user_unit,
            command=None,
        )

    def get_current_scheduled_job(self) -> ScheduledJobRecord | None:
        return self._scheduled_job_repository.get_current_job()

    def clear_current_scheduled_job(self) -> None:
        self._scheduled_job_repository.clear_current_job()

    def _resolve_action_command(self, action: PowerAction) -> list[str]:
        for service in self._action_services:
            if service.supports(action):
                return service.build_action_command(action)

        raise ValueError(f"Unsupported action: {action}")

    def _is_user_action(self, action: PowerAction) -> bool:
        for service in self._action_services:
            if service.supports(action):
                return service.is_user_level
        return False

    def _generate_unit_name(self, action: PowerAction) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"power-scheduler-{action.value}-{timestamp}"
