from __future__ import annotations

import unittest
from unittest.mock import Mock

from domain.enums import PowerAction
from services.scheduler_service import SchedulerService


class SchedulerServiceMiscTests(unittest.TestCase):
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
        self.shutdown_service.supports.return_value = True

        result = self.service._is_user_action(PowerAction.SUSPEND)

        self.assertFalse(result)

    def test_generate_unit_name_contains_action_value(self) -> None:
        unit_name = self.service._generate_unit_name(PowerAction.LOCK)

        self.assertTrue(unit_name.startswith("power-scheduler-lock-"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
