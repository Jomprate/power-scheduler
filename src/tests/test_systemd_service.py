from __future__ import annotations

import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main(verbosity=2)