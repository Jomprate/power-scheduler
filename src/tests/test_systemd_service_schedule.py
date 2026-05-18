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

    @patch("services.systemd_service.shutil.which")
    @patch("services.systemd_service.which_required")
    @patch("services.systemd_service.run_command")
    def test_schedule_system_unit_reminders_are_user_units(
        self, mock_run, mock_which_required, mock_shutil_which
    ) -> None:
        mock_run.return_value = Mock(returncode=0, stdout="started", stderr="")
        mock_which_required.return_value = "/usr/bin/systemd-run"
        mock_shutil_which.return_value = "/usr/bin/gapplication"

        params = SystemdScheduleParams(
            unit_name="power-scheduler-suspend-123",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=660,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        result = self.service.schedule(params)

        self.assertTrue(result.success)
        # 1 main unit + 2 reminders (10m and 5m for 11 min)
        self.assertEqual(mock_run.call_count, 3)

        # Main unit should NOT have --user
        main_call_args = mock_run.call_args_list[0][0][0]
        self.assertNotIn("--user", main_call_args)

        # Reminders MUST have --user so they can show notifications
        for reminder_call in mock_run.call_args_list[1:]:
            args = reminder_call[0][0]
            self.assertIn("--user", args)
            self.assertIn("reminder", args[args.index("--unit") + 1])
            self.assertIn("--timer-property=AccuracySec=1us", args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
