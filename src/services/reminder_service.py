from __future__ import annotations

from collections.abc import Callable
from functools import partial

from gi.repository import GLib

from domain.models import ScheduleRequest
from utils.time_utils import to_seconds


class ReminderService:
    """
    Schedules desktop reminder notifications at fixed intervals before
    a scheduled action is executed.

    Reminders only fire while the application is running.  If the
    application is closed, the underlying GLib timeouts are destroyed
    and no reminders will be shown.
    """

    _REMINDER_MINUTES = (10, 5)

    def __init__(self) -> None:
        self._notify_callback: Callable[[int, ScheduleRequest], None] | None = None
        self._timeout_ids: list[int] = []
        self._request: ScheduleRequest | None = None

    def set_notify_callback(
        self, callback: Callable[[int, ScheduleRequest], None]
    ) -> None:
        self._notify_callback = callback

    def schedule_reminders(self, request: ScheduleRequest) -> None:
        """Set up reminder timeouts for the given request."""
        self.clear_reminders()
        self._request = request
        total_seconds = to_seconds(request.amount, request.unit)

        for minutes_before in self._REMINDER_MINUTES:
            seconds_before = minutes_before * 60
            if total_seconds > seconds_before:
                delay_ms = (total_seconds - seconds_before) * 1000
                timeout_id = GLib.timeout_add(
                    delay_ms,
                    partial(self._on_reminder, minutes_before),
                )
                self._timeout_ids.append(timeout_id)

    def clear_reminders(self) -> None:
        """Cancel all pending reminder timeouts."""
        for timeout_id in self._timeout_ids:
            GLib.source_remove(timeout_id)
        self._timeout_ids.clear()
        self._request = None

    def _on_reminder(self, minutes_before: int) -> bool:
        if self._notify_callback is not None and self._request is not None:
            self._notify_callback(minutes_before, self._request)
        return False
