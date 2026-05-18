from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from services.systemd_service import SystemdScheduleParams, SystemdService


class SystemdServiceScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SystemdService()

    @patch.object(SystemdService, "_schedule_reminders")
    @patch("services.systemd_service.run_command")
    def test_schedule_user_unit_success(self, mock_run, _mock_reminders) -> None:
        mock_run.return_value = Mock(returncode=0, stdout="started", stderr="")
        params = SystemdScheduleParams(
            unit_name="power-scheduler-lock-123",
            command=["/usr/bin/loginctl", "lock-session", "42"],
            delay_seconds=10,
            is_user_unit=True,
            description="Power Scheduler: lock",
        )

        result = self.service.schedule(params)

        mock_run.assert_called_once()
        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, params.unit_name)
        self.assertTrue(result.is_user_unit)

    @patch.object(SystemdService, "_schedule_reminders")
    @patch("services.systemd_service.run_command")
    def test_schedule_system_unit_success(self, mock_run, _mock_reminders) -> None:
        mock_run.return_value = Mock(returncode=0, stdout="started", stderr="")
        params = SystemdScheduleParams(
            unit_name="power-scheduler-suspend-123",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=120,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        result = self.service.schedule(params)

        mock_run.assert_called_once()
        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, params.unit_name)
        self.assertFalse(result.is_user_unit)

    @patch.object(SystemdService, "_schedule_reminders")
    @patch("services.systemd_service.run_command")
    def test_schedule_polkit_error(self, mock_run, _mock_reminders) -> None:
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Authentication required")
        params = SystemdScheduleParams(
            unit_name="power-scheduler-suspend-123",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=60,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        result = self.service.schedule(params)

        self.assertFalse(result.success)
        self.assertIn("missing privileges", result.message)

    @patch.object(SystemdService, "_schedule_reminders")
    @patch("services.systemd_service.run_command")
    def test_schedule_generic_failure_includes_stderr(self, mock_run, _mock_reminders) -> None:
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Failed to start")
        params = SystemdScheduleParams(
            unit_name="power-scheduler-suspend-123",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=60,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        result = self.service.schedule(params)

        self.assertTrue(result.success)
        self.assertIn("Failed to start", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
