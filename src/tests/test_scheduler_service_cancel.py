from __future__ import annotations

import unittest
from unittest.mock import Mock

from services.scheduler_service import SchedulerService


class SchedulerServiceCancelTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
