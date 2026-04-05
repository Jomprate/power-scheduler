from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from domain.enums import PowerAction, TimeUnit
from domain.models import ScheduleRequest
from services.scheduler_service import SchedulerService


class SchedulerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session_service = Mock()
        self.shutdown_service = Mock()
        self.systemd_service = Mock()

        self.service = SchedulerService(
            session_service=self.session_service,
            shutdown_service=self.shutdown_service,
            systemd_service=self.systemd_service,
        )

    @patch("services.scheduler_service.validate_schedule_request")
    @patch("services.scheduler_service.format_human_time", return_value="15 seconds")
    @patch.object(
        SchedulerService,
        "_generate_unit_name",
        return_value="power-scheduler-lock-123",
    )
    def test_schedule_uses_session_service_for_user_actions(
        self,
        mock_generate_unit_name,
        mock_format_human_time,
        mock_validate_schedule_request,
    ) -> None:
        request = ScheduleRequest(
            action=PowerAction.LOCK,
            amount=15,
            unit=TimeUnit.SECONDS,
        )

        self.session_service.supports.side_effect = lambda action: action in {
            PowerAction.LOCK,
            PowerAction.LOG_OUT,
        }
        self.shutdown_service.supports.return_value = False

        self.session_service.build_action_command.return_value = [
            "/usr/bin/loginctl",
            "lock-session",
            "42",
        ]

        self.systemd_service.schedule.return_value = Mock(
            stdout="timer created",
            stderr="",
            command=[
                "/usr/bin/systemd-run",
                "--user",
                "--unit",
                "power-scheduler-lock-123",
                "/usr/bin/loginctl",
                "lock-session",
                "42",
            ],
        )

        result = self.service.schedule(request)

        mock_validate_schedule_request.assert_called_once_with(request)
        mock_generate_unit_name.assert_called_once_with(PowerAction.LOCK)
        mock_format_human_time.assert_called_once_with(15, TimeUnit.SECONDS)

        self.session_service.build_action_command.assert_called_once_with(
            PowerAction.LOCK
        )
        self.shutdown_service.build_action_command.assert_not_called()

        self.systemd_service.schedule.assert_called_once_with(
            unit_name="power-scheduler-lock-123",
            command=["/usr/bin/loginctl", "lock-session", "42"],
            delay_seconds=15,
            is_user_unit=True,
            description="Power Scheduler: lock",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-lock-123")
        self.assertTrue(result.is_user_unit)
        self.assertEqual(
            result.command,
            "/usr/bin/systemd-run --user --unit power-scheduler-lock-123 /usr/bin/loginctl lock-session 42",
        )
        self.assertEqual(
            result.message,
            "Scheduled lock in 15 seconds.\nUnit: power-scheduler-lock-123\ntimer created",
        )

    @patch("services.scheduler_service.validate_schedule_request")
    @patch("services.scheduler_service.format_human_time", return_value="2 minutes")
    @patch.object(
        SchedulerService,
        "_generate_unit_name",
        return_value="power-scheduler-suspend-123",
    )
    def test_schedule_uses_shutdown_service_for_system_actions(
        self,
        mock_generate_unit_name,
        mock_format_human_time,
        mock_validate_schedule_request,
    ) -> None:
        request = ScheduleRequest(
            action=PowerAction.SUSPEND,
            amount=2,
            unit=TimeUnit.MINUTES,
        )

        self.session_service.supports.return_value = False
        self.shutdown_service.supports.side_effect = lambda action: action in {
            PowerAction.SUSPEND,
            PowerAction.HIBERNATE,
            PowerAction.POWER_OFF,
        }
        self.shutdown_service.build_action_command.return_value = [
            "/usr/bin/systemctl",
            "suspend",
        ]

        self.systemd_service.schedule.return_value = Mock(
            stdout="",
            stderr="some warning",
            command=[
                "/usr/bin/systemd-run",
                "--unit",
                "power-scheduler-suspend-123",
                "/usr/bin/systemctl",
                "suspend",
            ],
        )

        result = self.service.schedule(request)

        mock_validate_schedule_request.assert_called_once_with(request)
        mock_generate_unit_name.assert_called_once_with(PowerAction.SUSPEND)
        mock_format_human_time.assert_called_once_with(2, TimeUnit.MINUTES)

        self.shutdown_service.build_action_command.assert_called_once_with(
            PowerAction.SUSPEND
        )
        self.session_service.build_action_command.assert_not_called()

        self.systemd_service.schedule.assert_called_once_with(
            unit_name="power-scheduler-suspend-123",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=120,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-suspend-123")
        self.assertFalse(result.is_user_unit)
        self.assertEqual(
            result.message,
            "Scheduled suspend in 2 minutes.\nUnit: power-scheduler-suspend-123\nsome warning",
        )

    @patch("services.scheduler_service.validate_schedule_request")
    @patch("services.scheduler_service.format_human_time", return_value="10 seconds")
    @patch.object(
        SchedulerService,
        "_generate_unit_name",
        return_value="power-scheduler-lock-456",
    )
    def test_schedule_includes_stdout_and_stderr_when_both_exist(
        self,
        mock_generate_unit_name,
        mock_format_human_time,
        mock_validate_schedule_request,
    ) -> None:
        request = ScheduleRequest(
            action=PowerAction.LOCK,
            amount=10,
            unit=TimeUnit.SECONDS,
        )

        self.session_service.supports.side_effect = lambda action: action in {
            PowerAction.LOCK,
            PowerAction.LOG_OUT,
        }
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

        mock_validate_schedule_request.assert_called_once_with(request)
        mock_generate_unit_name.assert_called_once_with(PowerAction.LOCK)
        mock_format_human_time.assert_called_once_with(10, TimeUnit.SECONDS)

        self.assertEqual(
            result.message,
            "Scheduled lock in 10 seconds.\nUnit: power-scheduler-lock-456\ncreated\nwarning",
        )

    def test_cancel_delegates_to_systemd_service(self) -> None:
        self.systemd_service.cancel.return_value = Mock(
            success=True,
            message="Cancelled scheduled action for unit: power-scheduler-lock-123",
            unit_name="power-scheduler-lock-123",
            is_user_unit=True,
        )

        result = self.service.cancel(
            unit_name="power-scheduler-lock-123",
            is_user_unit=True,
        )

        self.systemd_service.cancel.assert_called_once_with(
            unit_name="power-scheduler-lock-123",
            is_user_unit=True,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.message,
            "Cancelled scheduled action for unit: power-scheduler-lock-123",
        )
        self.assertEqual(result.unit_name, "power-scheduler-lock-123")
        self.assertTrue(result.is_user_unit)
        self.assertIsNone(result.command)

    def test_resolve_action_command_raises_for_unsupported_action(self) -> None:
        self.session_service.supports.return_value = False
        self.shutdown_service.supports.return_value = False

        with self.assertRaisesRegex(ValueError, "Unsupported action"):
            self.service._resolve_action_command(PowerAction.LOCK)

    def test_is_user_action_returns_true_for_session_actions(self) -> None:
        self.session_service.supports.return_value = True

        result = self.service._is_user_action(PowerAction.LOCK)

        self.assertTrue(result)
        self.session_service.supports.assert_called_once_with(PowerAction.LOCK)

    def test_is_user_action_returns_false_for_non_session_actions(self) -> None:
        self.session_service.supports.return_value = False

        result = self.service._is_user_action(PowerAction.SUSPEND)

        self.assertFalse(result)
        self.session_service.supports.assert_called_once_with(PowerAction.SUSPEND)

    def test_to_delay_seconds_returns_seconds_for_seconds_unit(self) -> None:
        self.assertEqual(
            self.service._to_delay_seconds(15, TimeUnit.SECONDS),
            15,
        )

    def test_to_delay_seconds_returns_seconds_for_minutes_unit(self) -> None:
        self.assertEqual(
            self.service._to_delay_seconds(3, TimeUnit.MINUTES),
            180,
        )

    def test_to_delay_seconds_returns_seconds_for_hours_unit(self) -> None:
        self.assertEqual(
            self.service._to_delay_seconds(2, TimeUnit.HOURS),
            7200,
        )

    def test_to_delay_seconds_raises_for_non_positive_amount(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Amount must be greater than zero",
        ):
            self.service._to_delay_seconds(0, TimeUnit.SECONDS)

    def test_to_delay_seconds_raises_for_unsupported_unit(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported time unit"):
            self.service._to_delay_seconds(1, "days")  # type: ignore[arg-type]

    def test_generate_unit_name_contains_action_value(self) -> None:
        unit_name = self.service._generate_unit_name(PowerAction.LOCK)

        self.assertTrue(unit_name.startswith("power-scheduler-lock-"))


if __name__ == "__main__":
    unittest.main(verbosity=2)