from __future__ import annotations

import unittest
from unittest.mock import Mock

from domain.enums import PowerAction, TimeUnit
from domain.models import ScheduleRequest
from services.notification_service import NotificationService
from services.scheduler_service import ScheduledJobResult


class NotificationServiceBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = NotificationService(Mock())

    def test_build_scheduled_title_for_lock(self) -> None:
        request = ScheduleRequest(
            action=PowerAction.LOCK,
            amount=10,
            unit=TimeUnit.SECONDS,
        )
        title = self.service._build_scheduled_title(request)
        self.assertEqual(title, "Lock scheduled")

    def test_build_scheduled_title_for_log_out(self) -> None:
        request = ScheduleRequest(
            action=PowerAction.LOG_OUT,
            amount=5,
            unit=TimeUnit.MINUTES,
        )
        title = self.service._build_scheduled_title(request)
        self.assertEqual(title, "Log Out scheduled")

    def test_build_scheduled_body(self) -> None:
        request = ScheduleRequest(
            action=PowerAction.SUSPEND,
            amount=30,
            unit=TimeUnit.SECONDS,
        )
        body = self.service._build_scheduled_body(request)
        self.assertEqual(
            body,
            "Will run in 30 seconds. Click this notification to cancel.",
        )

    def test_build_cancellation_body_preserves_non_cancelled_message(self) -> None:
        body = self.service._build_cancellation_body("Something else happened.")
        self.assertEqual(body, "Something else happened.")

    def test_build_cancellation_body_detects_cancelled(self) -> None:
        body = self.service._build_cancellation_body(
            "Cancelled scheduled action for unit: foo"
        )
        self.assertEqual(body, "The pending action was cancelled.")

    def test_build_cancellation_body_detects_canceled_alt_spelling(self) -> None:
        body = self.service._build_cancellation_body("Canceled by user")
        self.assertEqual(body, "The pending action was cancelled.")

    def test_build_cancellation_body_empty_fallback(self) -> None:
        body = self.service._build_cancellation_body("")
        self.assertEqual(body, "The pending action was cancelled.")

    def test_build_cancellation_body_whitespace_fallback(self) -> None:
        body = self.service._build_cancellation_body("   ")
        self.assertEqual(body, "The pending action was cancelled.")

    def test_build_error_body_preserves_message(self) -> None:
        body = self.service._build_error_body("Something went wrong.")
        self.assertEqual(body, "Something went wrong.")

    def test_build_error_body_empty_fallback(self) -> None:
        body = self.service._build_error_body("")
        self.assertEqual(body, "Something went wrong while processing the action.")

    def test_format_action_label_underscores_to_spaces(self) -> None:
        label = self.service._format_action_label("log_out")
        self.assertEqual(label, "Log Out")

    def test_format_action_label_single_word(self) -> None:
        label = self.service._format_action_label("suspend")
        self.assertEqual(label, "Suspend")

    def test_format_action_label_empty_string(self) -> None:
        label = self.service._format_action_label("")
        self.assertEqual(label, "Action")


class NotificationServicePublicTests(unittest.TestCase):
    def test_send_scheduled_notification_calls_application(self) -> None:
        app = Mock()
        service = NotificationService(app)
        request = ScheduleRequest(
            action=PowerAction.LOCK,
            amount=10,
            unit=TimeUnit.SECONDS,
        )
        result = ScheduledJobResult(
            success=True,
            message="Scheduled",
            unit_name="test-unit",
        )

        service.send_scheduled_notification(request, result)

        app.send_notification.assert_called_once()
        args, _ = app.send_notification.call_args
        self.assertEqual(args[0], NotificationService.SCHEDULED_NOTIFICATION_ID)

    def test_send_cancellation_notification_calls_application(self) -> None:
        app = Mock()
        service = NotificationService(app)

        service.send_cancellation_notification("Cancelled")

        self.assertGreaterEqual(app.send_notification.call_count, 1)
        app.withdraw_notification.assert_called_once_with(
            NotificationService.SCHEDULED_NOTIFICATION_ID,
        )

    def test_send_error_notification_calls_application(self) -> None:
        app = Mock()
        service = NotificationService(app)

        service.send_error_notification("Error!")

        app.send_notification.assert_called_once()
        args, _ = app.send_notification.call_args
        self.assertEqual(args[0], NotificationService.ERROR_NOTIFICATION_ID)

    def test_withdraw_scheduled_notification_calls_application(self) -> None:
        app = Mock()
        service = NotificationService(app)

        service.withdraw_scheduled_notification()

        app.withdraw_notification.assert_called_once_with(
            NotificationService.SCHEDULED_NOTIFICATION_ID,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
