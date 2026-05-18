from __future__ import annotations

from dataclasses import dataclass

from domain.enums import PowerAction, TimeUnit
from domain.models import ScheduledJobResult, ScheduleRequest
from services.reminder_service import ReminderService
from services.scheduler_service import SchedulerService


@dataclass
class JobState:
    unit_name: str
    is_user_unit: bool
    command: str | None
    action: PowerAction | None = None
    amount: int | None = None
    unit: TimeUnit | None = None


class ScheduleController:
    def __init__(
        self,
        scheduler_service: SchedulerService,
        reminder_service: ReminderService,
    ) -> None:
        self._scheduler_service = scheduler_service
        self._reminder_service = reminder_service
        self._active_job: JobState | None = None
        self._sync()

    def schedule(self, request: ScheduleRequest) -> ScheduledJobResult:
        result = self._scheduler_service.schedule(request)
        self._sync()
        if result.success:
            self._reminder_service.schedule_reminders(request)
        return result

    def cancel(self) -> ScheduledJobResult | None:
        self._reminder_service.clear_reminders()

        if self._active_job is None:
            return None

        try:
            result = self._scheduler_service.cancel(
                self._active_job.unit_name,
                self._active_job.is_user_unit,
            )
            return result
        except Exception as exc:
            return ScheduledJobResult(success=False, message=str(exc))
        finally:
            self._sync()

    def restore_if_any(self) -> JobState | None:
        self._sync()
        return self._active_job

    @property
    def active_job(self) -> JobState | None:
        return self._active_job

    def _sync(self) -> None:
        stored = self._scheduler_service.get_current_scheduled_job()
        if stored is None:
            self._active_job = None
        else:
            self._active_job = JobState(
                unit_name=stored.unit_name,
                is_user_unit=stored.is_user_unit,
                command=stored.command,
                action=stored.action,
                amount=stored.amount,
                unit=stored.unit,
            )
