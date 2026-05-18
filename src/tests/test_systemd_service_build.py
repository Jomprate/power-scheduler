from __future__ import annotations

import unittest

from services.systemd_service import SystemdScheduleParams, SystemdService


class SystemdServiceBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SystemdService()

    def test_build_schedule_command_user_unit(self) -> None:
        params = SystemdScheduleParams(
            unit_name="power-scheduler-lock-123",
            command=["/usr/bin/loginctl", "lock-session", "42"],
            delay_seconds=10,
            is_user_unit=True,
            description="Power Scheduler: lock",
        )

        cmd = self.service.build_schedule_command(params)

        self.assertIn("systemd-run", cmd[0])
        self.assertIn("--user", cmd)
        self.assertIn("--unit", cmd)
        self.assertIn(params.unit_name, cmd)
        self.assertIn("--on-active", cmd)
        self.assertIn("10s", cmd)
        self.assertIn("--description", cmd)
        self.assertIn("Power Scheduler: lock", cmd)
        self.assertIn("/usr/bin/loginctl", cmd)

    def test_build_schedule_command_system_unit(self) -> None:
        params = SystemdScheduleParams(
            unit_name="power-scheduler-suspend-123",
            command=["/usr/bin/systemctl", "suspend"],
            delay_seconds=120,
            is_user_unit=False,
            description="Power Scheduler: suspend",
        )

        cmd = self.service.build_schedule_command(params)

        self.assertIn("systemd-run", cmd[0])
        self.assertNotIn("--user", cmd)
        self.assertIn("--unit", cmd)
        self.assertIn(params.unit_name, cmd)
        self.assertIn("120s", cmd)
        self.assertIn("/usr/bin/systemctl", cmd)

    def test_build_schedule_command_omits_blank_description(self) -> None:
        params = SystemdScheduleParams(
            unit_name="power-scheduler-test",
            command=["/usr/bin/true"],
            delay_seconds=1,
            is_user_unit=True,
            description="   ",
        )

        cmd = self.service.build_schedule_command(params)

        self.assertNotIn("--description", cmd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
