from __future__ import annotations

from gi.repository import Gio

from domain.models import ScheduleRequest
from services.scheduler_service import ScheduledJobResult
from utils.time_utils import format_human_time


class NotificationService:
    """
    Sends desktop notifications through Gio.Notification.

    Current behavior:
    - clicking the notification body triggers app.cancel-scheduled
    - the actual unit to cancel is resolved by the application from the
      stored scheduled job repository
    - notification text stays user-friendly
    """

    SCHEDULED_NOTIFICATION_ID = "scheduled-job"
    INFO_NOTIFICATION_ID = "info"
    ERROR_NOTIFICATION_ID = "error"

    def __init__(self, application: Gio.Application) -> None:
        self._application = application

    def send_scheduled_notification(
        self,
        request: ScheduleRequest,
        result: ScheduledJobResult,
    ) -> None:
        notification = Gio.Notification.new(
            self._build_scheduled_title(request)
        )
        notification.set_body(self._build_scheduled_body(request))
        notification.set_priority(Gio.NotificationPriority.NORMAL)
        notification.set_default_action("app.cancel-scheduled")

        self._application.send_notification(
            self.SCHEDULED_NOTIFICATION_ID,
            notification,
        )

    def send_cancellation_notification(self, message: str) -> None:
        notification = Gio.Notification.new("Scheduled action cancelled")
        notification.set_body(self._build_cancellation_body(message))
        notification.set_priority(Gio.NotificationPriority.NORMAL)

        self._application.send_notification(
            self.INFO_NOTIFICATION_ID,
            notification,
        )
        self.withdraw_scheduled_notification()

    def send_error_notification(self, message: str) -> None:
        notification = Gio.Notification.new("Power Scheduler error")
        notification.set_body(self._build_error_body(message))
        notification.set_priority(Gio.NotificationPriority.HIGH)

        self._application.send_notification(
            self.ERROR_NOTIFICATION_ID,
            notification,
        )

    def withdraw_scheduled_notification(self) -> None:
        self._application.withdraw_notification(self.SCHEDULED_NOTIFICATION_ID)

    def _build_scheduled_title(self, request: ScheduleRequest) -> str:
        return f"{self._format_action_label(request.action.value)} scheduled"

    def _build_scheduled_body(self, request: ScheduleRequest) -> str:
        delay_label = format_human_time(request.amount, request.unit)
        return f"Will run in {delay_label}. Click this notification to cancel."

    def _build_cancellation_body(self, message: str) -> str:
        normalized = " ".join(message.strip().split())

        if not normalized:
            return "The pending action was cancelled."

        lowered = normalized.lower()
        if "cancelled" in lowered or "canceled" in lowered:
            return "The pending action was cancelled."

        return normalized

    def _build_error_body(self, message: str) -> str:
        normalized = " ".join(message.strip().split())
        if not normalized:
            return "Something went wrong while processing the action."
        return normalized

    @staticmethod
    def _format_action_label(action_value: str) -> str:
        text = action_value.strip().replace("_", " ")
        if not text:
            return "Action"

        words = text.split()
        return " ".join(word.capitalize() for word in words)