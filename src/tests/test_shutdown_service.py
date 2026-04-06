from __future__ import annotations

import unittest
from unittest.mock import patch

from domain.enums import PowerAction
from services.shutdown_service import ShutdownService


class ShutdownServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ShutdownService()

    def test_supports_returns_true_for_shutdown_actions(self) -> None:
        self.assertTrue(self.service.supports(PowerAction.SUSPEND))
        self.assertTrue(self.service.supports(PowerAction.HIBERNATE))
        self.assertTrue(self.service.supports(PowerAction.POWER_OFF))

    def test_supports_returns_false_for_non_shutdown_actions(self) -> None:
        self.assertFalse(self.service.supports(PowerAction.LOCK))
        self.assertFalse(self.service.supports(PowerAction.LOG_OUT))

    @patch("services.shutdown_service.shutil.which", return_value="/usr/bin/systemctl")
    def test_build_action_command_returns_suspend_command(
        self,
        _mock_which,
    ) -> None:
        command = self.service.build_action_command(PowerAction.SUSPEND)

        self.assertEqual(
            command,
            ["/usr/bin/systemctl", "start", "suspend.target"],
        )

    @patch("services.shutdown_service.shutil.which", return_value="/usr/bin/systemctl")
    def test_build_action_command_returns_hibernate_command(
        self,
        _mock_which,
    ) -> None:
        command = self.service.build_action_command(PowerAction.HIBERNATE)

        self.assertEqual(
            command,
            ["/usr/bin/systemctl", "start", "hibernate.target"],
        )

    @patch("services.shutdown_service.shutil.which", return_value="/usr/bin/systemctl")
    def test_build_action_command_returns_poweroff_command(
        self,
        _mock_which,
    ) -> None:
        command = self.service.build_action_command(PowerAction.POWER_OFF)

        self.assertEqual(
            command,
            ["/usr/bin/systemctl", "start", "poweroff.target"],
        )

    @patch("services.shutdown_service.shutil.which", return_value=None)
    def test_build_action_command_raises_when_systemctl_is_missing(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "Required binary not found: systemctl",
        ):
            self.service.build_action_command(PowerAction.HIBERNATE)

    @patch("services.shutdown_service.shutil.which", return_value="/usr/bin/systemctl")
    def test_build_action_command_raises_for_unsupported_action(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported shutdown action",
        ):
            self.service.build_action_command(PowerAction.LOCK)


if __name__ == "__main__":
    unittest.main(verbosity=2)