from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.enums import PowerAction, TimeUnit
from domain.models import ScheduleRequest
from domain.validators import validate_schedule_request
from repositories.scheduled_job_repository import (
    ScheduledJobRecord,
    ScheduledJobRepository,
)
from services.session_service import SessionService
from services.shutdown_service import ShutdownService
from services.systemd_service import SystemdService
from utils.time_utils import format_human_time


@dataclass(slots=True)
class ScheduledJobResult:
    success: bool
    message: str
    unit_name: str | None = None
    is_user_unit: bool = False
    command: str | None = None


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
        session_service: SessionService | None = None,
        shutdown_service: ShutdownService | None = None,
        systemd_service: SystemdService | None = None,
        scheduled_job_repository: ScheduledJobRepository | None = None,
    ) -> None:
        self.session_service = session_service or SessionService()
        self.shutdown_service = shutdown_service or ShutdownService()
        self.systemd_service = systemd_service or SystemdService()
        self.scheduled_job_repository = (
            scheduled_job_repository or ScheduledJobRepository()
        )

    def schedule(self, request: ScheduleRequest) -> ScheduledJobResult:
        validate_schedule_request(request)

        unit_name = self._generate_unit_name(request.action)
        is_user_unit = self._is_user_action(request.action)
        action_command = self._resolve_action_command(request.action)
        delay_seconds = self._to_delay_seconds(request.amount, request.unit)

        result = self.systemd_service.schedule(
            unit_name=unit_name,
            command=action_command,
            delay_seconds=delay_seconds,
            is_user_unit=is_user_unit,
            description=f"Power Scheduler: {request.action.value}",
        )

        scheduled_for = format_human_time(request.amount, request.unit)
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

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
            command=" ".join(result.command),
        )

        self.scheduled_job_repository.save_current_job(
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
        result = self.systemd_service.cancel(
            unit_name=unit_name,
            is_user_unit=is_user_unit,
        )

        if result.success:
            stored_job = self.scheduled_job_repository.get_current_job()
            if stored_job is None or stored_job.unit_name == unit_name:
                self.scheduled_job_repository.clear_current_job()

        return ScheduledJobResult(
            success=result.success,
            message=result.message,
            unit_name=result.unit_name,
            is_user_unit=result.is_user_unit,
            command=None,
        )

    def get_current_scheduled_job(self) -> ScheduledJobRecord | None:
        return self.scheduled_job_repository.get_current_job()

    def clear_current_scheduled_job(self) -> None:
        self.scheduled_job_repository.clear_current_job()

    def _resolve_action_command(self, action: PowerAction) -> list[str]:
        if self.session_service.supports(action):
            return self.session_service.build_action_command(action)

        if self.shutdown_service.supports(action):
            return self.shutdown_service.build_action_command(action)

        raise ValueError(f"Unsupported action: {action}")

    def _is_user_action(self, action: PowerAction) -> bool:
        return self.session_service.supports(action)

    def _generate_unit_name(self, action: PowerAction) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"power-scheduler-{action.value}-{timestamp}"

    @staticmethod
    def _to_delay_seconds(amount: int, unit: TimeUnit) -> int:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        if unit == TimeUnit.SECONDS:
            return amount

        if unit == TimeUnit.MINUTES:
            return amount * 60

        if unit == TimeUnit.HOURS:
            return amount * 3600

        raise ValueError(f"Unsupported time unit: {unit}")