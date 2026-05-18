from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from domain.enums import PowerAction, TimeUnit
from domain.models import ScheduleRequest
from services.scheduler_service import SchedulerService
from services.systemd_service import SystemdScheduleParams


class SchedulerServiceScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session_service = Mock()
        self.session_service.is_user_level = True
        self.shutdown_service = Mock()
        self.shutdown_service.is_user_level = False
        self.systemd_service = Mock()
        self.scheduled_job_repository = Mock()

        self.service = SchedulerService(
            action_services=[self.session_service, self.shutdown_service],
            systemd_service=self.systemd_service,
            scheduled_job_repository=self.scheduled_job_repository,
        )

    @patch("services.scheduler_service.format_human_time", return_value="15 seconds")
    @patch.object(
        SchedulerService,
        "_generate_unit_name",
        return_value="power-scheduler-lock-123",
    )
    def test_schedule_user_action(self, mock_generate, mock_format) -> None:
        request = ScheduleRequest(
            action=PowerAction.LOCK, amount=15, unit=TimeUnit.SECONDS
        )
        self.session_service.supports.return_value = True
        self.shutdown_service.supports.return_value = False
        self.session_service.build_action_command.return_value = [
            "/usr/bin/loginctl",
            "lock-session",
            "42",
        ]
        self.systemd_service.schedule.return_value = Mock(
            stdout="timer created",
            stderr="",
            command=["cmd"],
        )

        result = self.service.schedule(request)

        mock_generate.assert_called_once_with(PowerAction.LOCK)
        mock_format.assert_called_once_with(15, TimeUnit.SECONDS)
        self.session_service.build_action_command.assert_called_once_with(PowerAction.LOCK)
        self.shutdown_service.build_action_command.assert_not_called()
        self.systemd_service.schedule.assert_called_once_with(
            SystemdScheduleParams(
                unit_name="power-scheduler-lock-123",
                command=["/usr/bin/loginctl", "lock-session", "42"],
                delay_seconds=15,
                is_user_unit=True,
                description="Power Scheduler: lock",
            )
        )
        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-lock-123")
        self.assertTrue(result.is_user_unit)

    @patch("services.scheduler_service.format_human_time", return_value="2 minutes")
    @patch.object(
        SchedulerService,
        "_generate_unit_name",
        return_value="power-scheduler-suspend-123",
    )
    def test_schedule_system_action(self, mock_generate, mock_format) -> None:
        request = ScheduleRequest(
            action=PowerAction.SUSPEND, amount=2, unit=TimeUnit.MINUTES
        )
        self.session_service.supports.return_value = False
        self.shutdown_service.supports.return_value = True
        self.shutdown_service.build_action_command.return_value = [
            "/usr/bin/systemctl",
            "suspend",
        ]
        self.systemd_service.schedule.return_value = Mock(
            stdout="",
            stderr="some warning",
            command=["cmd"],
        )

        result = self.service.schedule(request)

        mock_generate.assert_called_once_with(PowerAction.SUSPEND)
        mock_format.assert_called_once_with(2, TimeUnit.MINUTES)
        self.shutdown_service.build_action_command.assert_called_once_with(PowerAction.SUSPEND)
        self.session_service.build_action_command.assert_not_called()
        self.systemd_service.schedule.assert_called_once_with(
            SystemdScheduleParams(
                unit_name="power-scheduler-suspend-123",
                command=["/usr/bin/systemctl", "suspend"],
                delay_seconds=120,
                is_user_unit=False,
                description="Power Scheduler: suspend",
            )
        )
        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-suspend-123")
        self.assertFalse(result.is_user_unit)
        self.assertEqual(
            result.message,
            "Scheduled suspend in 2 minutes.\nUnit: power-scheduler-suspend-123\nsome warning",
        )

    @patch("services.scheduler_service.format_human_time", return_value="10 seconds")
    @patch.object(
        SchedulerService,
        "_generate_unit_name",
        return_value="power-scheduler-lock-456",
    )
    def test_schedule_includes_stdout_and_stderr(self, mock_generate, mock_format) -> None:
        request = ScheduleRequest(
            action=PowerAction.LOCK, amount=10, unit=TimeUnit.SECONDS
        )
        self.session_service.supports.return_value = True
        self.shutdown_service.supports.return_value = False
        self.session_service.build_action_command.return_value = [
            "/usr/bin/loginctl",
            "lock-session",
            "42",
        ]
        self.systemd_service.schedule.return_value = Mock(
            stdout="created",
            stderr="warning",
            command=["cmd", "arg"],
        )

        result = self.service.schedule(request)

        mock_generate.assert_called_once_with(PowerAction.LOCK)
        mock_format.assert_called_once_with(10, TimeUnit.SECONDS)
        self.assertEqual(
            result.message,
            "Scheduled lock in 10 seconds.\nUnit: power-scheduler-lock-456\ncreated\nwarning",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
