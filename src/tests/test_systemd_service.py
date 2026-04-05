from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from services.systemd_service import SystemdService


class SystemdServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SystemdService()

    @patch("services.systemd_service.shutil.which")
    def test_build_schedule_command_for_user_unit(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "systemd-run":
                return "/usr/bin/systemd-run"
            return None

        mock_which.side_effect = which_side_effect

        command = self.service.build_schedule_command(
            unit_name="power-scheduler-lock-test",
            command=["/usr/bin/loginctl", "lock-session", "42"],
            delay_seconds=15,
            is_user_unit=True,
            description="Power Scheduler: lock",
        )

        self.assertEqual(
            command,
            [
                "/usr/bin/systemd-run",
                "--user",
                "--no-block",
                "--unit",
                "power-scheduler-lock-test",
                "--on-active",
                "15s",
                "--timer-property=AccuracySec=1us",
                "--collect",
                "--property=Type=oneshot",
                "--description",
                "Power Scheduler: lock",
                "/usr/bin/loginctl",
                "lock-session",
                "42",
            ],
            "User schedule command should include --user, no-block and high timer accuracy.",
        )

    @patch("services.systemd_service.shutil.which")
    def test_build_schedule_command_for_system_unit(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "systemd-run":
                return "/usr/bin/systemd-run"
            return None

        mock_which.side_effect = which_side_effect

        command = self.service.build_schedule_command(
            unit_name="power-scheduler-suspend-test",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=30,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        self.assertEqual(
            command,
            [
                "/usr/bin/systemd-run",
                "--no-block",
                "--unit",
                "power-scheduler-suspend-test",
                "--on-active",
                "30s",
                "--timer-property=AccuracySec=1us",
                "--collect",
                "--property=Type=oneshot",
                "--description",
                "Power Scheduler: suspend",
                "/usr/bin/systemctl",
                "suspend",
            ],
            "System schedule command should omit --user and keep the timer accuracy property.",
        )

    @patch("services.systemd_service.shutil.which")
    def test_build_schedule_command_omits_blank_description(
        self,
        mock_which,
    ) -> None:
        mock_which.return_value = "/usr/bin/systemd-run"

        command = self.service.build_schedule_command(
            unit_name="power-scheduler-test",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=10,
            is_user_unit=False,
            description="   ",
        )

        self.assertEqual(
            command,
            [
                "/usr/bin/systemd-run",
                "--no-block",
                "--unit",
                "power-scheduler-test",
                "--on-active",
                "10s",
                "--timer-property=AccuracySec=1us",
                "--collect",
                "--property=Type=oneshot",
                "/usr/bin/systemctl",
                "suspend",
            ],
            "Blank descriptions should not be included in the final systemd-run command.",
        )

    @patch("services.systemd_service.shutil.which")
    def test_build_systemctl_base_for_user_unit(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "systemctl":
                return "/usr/bin/systemctl"
            return None

        mock_which.side_effect = which_side_effect

        base_command = self.service._build_systemctl_base(True)

        self.assertEqual(
            base_command,
            ["/usr/bin/systemctl", "--user"],
            "User systemctl base command should include --user.",
        )

    @patch("services.systemd_service.shutil.which")
    def test_build_systemctl_base_for_system_unit(
        self,
        mock_which,
    ) -> None:
        mock_which.return_value = "/usr/bin/systemctl"

        base_command = self.service._build_systemctl_base(False)

        self.assertEqual(
            base_command,
            ["/usr/bin/systemctl"],
            "System systemctl base command should not include --user.",
        )

    @patch("services.systemd_service.shutil.which")
    def test_build_schedule_command_raises_when_systemd_run_is_missing(
        self,
        mock_which,
    ) -> None:
        mock_which.return_value = None

        with self.assertRaisesRegex(
            RuntimeError,
            "Required binary not found: systemd-run",
        ):
            self.service.build_schedule_command(
                unit_name="power-scheduler-test",
                command=["/usr/bin/systemctl", "suspend"],
                delay_seconds=10,
                is_user_unit=False,
                description="Power Scheduler: test",
            )

    @patch("services.systemd_service.shutil.which")
    def test_build_systemctl_base_raises_when_systemctl_is_missing(
        self,
        mock_which,
    ) -> None:
        mock_which.return_value = None

        with self.assertRaisesRegex(
            RuntimeError,
            "Required binary not found: systemctl",
        ):
            self.service._build_systemctl_base(False)

    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemd-run")
    def test_build_schedule_command_raises_when_unit_name_is_empty(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "unit_name cannot be empty"):
            self.service.build_schedule_command(
                unit_name="",
                command=["/usr/bin/systemctl", "suspend"],
                delay_seconds=10,
                is_user_unit=False,
                description="Power Scheduler: test",
            )

    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemd-run")
    def test_build_schedule_command_raises_when_command_is_empty(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "command cannot be empty"):
            self.service.build_schedule_command(
                unit_name="power-scheduler-test",
                command=[],
                delay_seconds=10,
                is_user_unit=False,
                description="Power Scheduler: test",
            )

    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemd-run")
    def test_build_schedule_command_raises_when_command_contains_empty_part(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "command cannot contain empty parts",
        ):
            self.service.build_schedule_command(
                unit_name="power-scheduler-test",
                command=["/usr/bin/systemctl", ""],
                delay_seconds=10,
                is_user_unit=False,
                description="Power Scheduler: test",
            )

    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemd-run")
    def test_build_schedule_command_raises_when_delay_is_not_positive(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "delay_seconds must be greater than zero",
        ):
            self.service.build_schedule_command(
                unit_name="power-scheduler-test",
                command=["/usr/bin/systemctl", "suspend"],
                delay_seconds=0,
                is_user_unit=False,
                description="Power Scheduler: test",
            )

    @patch("services.systemd_service.run_command")
    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemd-run")
    def test_schedule_returns_result_with_trimmed_stdout_and_stderr(
        self,
        _mock_which,
        mock_run_command,
    ) -> None:
        mock_run_command.return_value = SimpleNamespace(
            stdout="  timer created successfully  \n",
            stderr="  warning text  \n",
        )

        result = self.service.schedule(
            unit_name="power-scheduler-lock-test",
            command=["/usr/bin/loginctl", "lock-session", "42"],
            delay_seconds=15,
            is_user_unit=True,
            description="Power Scheduler: lock",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-lock-test")
        self.assertTrue(result.is_user_unit)
        self.assertEqual(result.message, "Scheduled transient unit: power-scheduler-lock-test")
        self.assertEqual(result.stdout, "timer created successfully")
        self.assertEqual(result.stderr, "warning text")
        self.assertEqual(
            result.command,
            [
                "/usr/bin/systemd-run",
                "--user",
                "--no-block",
                "--unit",
                "power-scheduler-lock-test",
                "--on-active",
                "15s",
                "--timer-property=AccuracySec=1us",
                "--collect",
                "--property=Type=oneshot",
                "--description",
                "Power Scheduler: lock",
                "/usr/bin/loginctl",
                "lock-session",
                "42",
            ],
        )

        mock_run_command.assert_called_once_with(
            [
                "/usr/bin/systemd-run",
                "--user",
                "--no-block",
                "--unit",
                "power-scheduler-lock-test",
                "--on-active",
                "15s",
                "--timer-property=AccuracySec=1us",
                "--collect",
                "--property=Type=oneshot",
                "--description",
                "Power Scheduler: lock",
                "/usr/bin/loginctl",
                "lock-session",
                "42",
            ]
        )

    def test_schedule_raises_when_unit_name_is_blank(self) -> None:
        with self.assertRaisesRegex(ValueError, "unit_name cannot be empty"):
            self.service.schedule(
                unit_name="   ",
                command=["/usr/bin/systemctl", "suspend"],
                delay_seconds=10,
                is_user_unit=False,
                description="Power Scheduler: suspend",
            )

    def test_schedule_raises_when_command_is_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "command cannot be empty"):
            self.service.schedule(
                unit_name="power-scheduler-test",
                command=[],
                delay_seconds=10,
                is_user_unit=False,
                description="Power Scheduler: suspend",
            )

    def test_schedule_raises_when_delay_is_not_positive(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "delay_seconds must be greater than zero",
        ):
            self.service.schedule(
                unit_name="power-scheduler-test",
                command=["/usr/bin/systemctl", "suspend"],
                delay_seconds=-1,
                is_user_unit=False,
                description="Power Scheduler: suspend",
            )

    @patch("services.systemd_service.run_command")
    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemctl")
    def test_cancel_for_user_unit_executes_expected_sequence(
        self,
        _mock_which,
        mock_run_command,
    ) -> None:
        result = self.service.cancel(
            unit_name="power-scheduler-lock-test",
            is_user_unit=True,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.message,
            "Cancelled scheduled action for unit: power-scheduler-lock-test",
        )
        self.assertEqual(result.unit_name, "power-scheduler-lock-test")
        self.assertTrue(result.is_user_unit)

        self.assertEqual(
            mock_run_command.call_args_list,
            [
                call(
                    ["/usr/bin/systemctl", "--user", "stop", "power-scheduler-lock-test.timer"],
                    check=False,
                ),
                call(
                    ["/usr/bin/systemctl", "--user", "stop", "power-scheduler-lock-test.service"],
                    check=False,
                ),
                call(
                    ["/usr/bin/systemctl", "--user", "reset-failed", "power-scheduler-lock-test.timer"],
                    check=False,
                ),
                call(
                    ["/usr/bin/systemctl", "--user", "reset-failed", "power-scheduler-lock-test.service"],
                    check=False,
                ),
            ],
        )

    @patch("services.systemd_service.run_command")
    @patch("services.systemd_service.shutil.which", return_value="/usr/bin/systemctl")
    def test_cancel_for_system_unit_executes_expected_sequence(
        self,
        _mock_which,
        mock_run_command,
    ) -> None:
        result = self.service.cancel(
            unit_name="power-scheduler-suspend-test",
            is_user_unit=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            mock_run_command.call_args_list,
            [
                call(
                    ["/usr/bin/systemctl", "stop", "power-scheduler-suspend-test.timer"],
                    check=False,
                ),
                call(
                    ["/usr/bin/systemctl", "stop", "power-scheduler-suspend-test.service"],
                    check=False,
                ),
                call(
                    ["/usr/bin/systemctl", "reset-failed", "power-scheduler-suspend-test.timer"],
                    check=False,
                ),
                call(
                    ["/usr/bin/systemctl", "reset-failed", "power-scheduler-suspend-test.service"],
                    check=False,
                ),
            ],
        )

    def test_cancel_raises_when_unit_name_is_blank(self) -> None:
        with self.assertRaisesRegex(ValueError, "unit_name cannot be empty"):
            self.service.cancel(
                unit_name="   ",
                is_user_unit=False,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)