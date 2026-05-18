from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from services.systemd_service import SystemdService


class SystemdServiceCancelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SystemdService()

    @patch("services.systemd_service.run_command")
    def test_cancel_user_unit_success(self, mock_run) -> None:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = self.service.cancel(
            unit_name="power-scheduler-lock-123",
            is_user_unit=True,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-lock-123")
        self.assertTrue(result.is_user_unit)

    @patch("services.systemd_service.run_command")
    def test_cancel_system_unit_success(self, mock_run) -> None:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = self.service.cancel(
            unit_name="power-scheduler-suspend-123",
            is_user_unit=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.unit_name, "power-scheduler-suspend-123")
        self.assertFalse(result.is_user_unit)

    @patch("services.systemd_service.run_command")
    def test_cancel_ignores_not_loaded(self, mock_run) -> None:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Failed to stop power-scheduler-lock-123.timer: Unit power-scheduler-lock-123.timer not loaded.",
        )

        result = self.service.cancel(
            unit_name="power-scheduler-lock-123",
            is_user_unit=True,
        )

        self.assertTrue(result.success)
        self.assertIn("Cancelled scheduled action for unit: power-scheduler-lock-123", result.message)

    @patch("services.systemd_service.run_command")
    def test_cancel_reports_real_failure(self, mock_run) -> None:
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Permission denied")

        result = self.service.cancel(
            unit_name="power-scheduler-suspend-123",
            is_user_unit=False,
        )

        self.assertFalse(result.success)
        self.assertIn("Permission denied", result.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
