from __future__ import annotations

import unittest

from domain.enums import PowerAction, TimeUnit
from repositories.scheduled_job_repository import ScheduledJobRecord


class ScheduledJobRecordTests(unittest.TestCase):
    def test_to_json_dict_contains_all_fields(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-lock-test",
            is_user_unit=True,
            action=PowerAction.LOCK,
            amount=15,
            unit=TimeUnit.SECONDS,
            command="/usr/bin/loginctl lock-session 42",
            created_at="2025-01-01T00:00:00+00:00",
        )
        data = record.to_json_dict()

        self.assertEqual(data["unit_name"], "power-scheduler-lock-test")
        self.assertTrue(data["is_user_unit"])
        self.assertEqual(data["action"], "lock")
        self.assertEqual(data["amount"], 15)
        self.assertEqual(data["unit"], "seconds")
        self.assertEqual(data["command"], "/usr/bin/loginctl lock-session 42")
        self.assertEqual(data["created_at"], "2025-01-01T00:00:00+00:00")

    def test_to_json_dict_defaults_command_and_created_at_to_none(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-suspend-test",
            is_user_unit=False,
            action=PowerAction.SUSPEND,
            amount=5,
            unit=TimeUnit.MINUTES,
        )
        data = record.to_json_dict()

        self.assertIsNone(data["command"])
        self.assertIsNone(data["created_at"])

    def test_from_json_dict_round_trip(self) -> None:
        original = ScheduledJobRecord(
            unit_name="power-scheduler-hibernate-test",
            is_user_unit=False,
            action=PowerAction.HIBERNATE,
            amount=2,
            unit=TimeUnit.HOURS,
            command="/usr/bin/systemctl hibernate",
            created_at="2025-06-15T12:30:00+00:00",
        )
        data = original.to_json_dict()
        restored = ScheduledJobRecord.from_json_dict(data)

        self.assertEqual(restored.unit_name, original.unit_name)
        self.assertEqual(restored.is_user_unit, original.is_user_unit)
        self.assertEqual(restored.action, original.action)
        self.assertEqual(restored.amount, original.amount)
        self.assertEqual(restored.unit, original.unit)
        self.assertEqual(restored.command, original.command)
        self.assertEqual(restored.created_at, original.created_at)

    def test_from_json_dict_minimal_fields(self) -> None:
        data = {
            "unit_name": "power-scheduler-poweroff-test",
            "is_user_unit": False,
            "action": "power_off",
            "amount": 1,
            "unit": "hours",
        }
        record = ScheduledJobRecord.from_json_dict(data)

        self.assertEqual(record.unit_name, "power-scheduler-poweroff-test")
        self.assertFalse(record.is_user_unit)
        self.assertEqual(record.action, PowerAction.POWER_OFF)
        self.assertEqual(record.amount, 1)
        self.assertEqual(record.unit, TimeUnit.HOURS)
        self.assertIsNone(record.command)
        self.assertIsNone(record.created_at)

    def test_from_json_dict_validations(self) -> None:
        cases = [
            (
                {"unit_name": "", "action": "lock", "amount": 10},
                None,
                "raises for empty unit_name",
            ),
            (
                {"unit_name": "test", "action": "lock", "amount": 0},
                "greater than zero",
                "raises for non-positive amount",
            ),
            (
                {"unit_name": "test", "action": "lock", "amount": True},
                "not a boolean",
                "raises for bool amount",
            ),
            (
                {
                    "unit_name": "test",
                    "action": "unknown_action",
                    "amount": 10,
                },
                None,
                "raises for unknown action",
            ),
        ]

        for overrides, msg, label in cases:
            with self.subTest(label=label):
                data = {
                    "is_user_unit": False,
                    "unit": "seconds",
                    **overrides,
                }
                if msg:
                    with self.assertRaisesRegex(ValueError, msg):
                        ScheduledJobRecord.from_json_dict(data)
                else:
                    with self.assertRaises(ValueError):
                        ScheduledJobRecord.from_json_dict(data)

    def test_from_json_dict_command_normalization(self) -> None:
        cases = [
            (None, "null command"),
            ("   ", "empty command string"),
        ]

        for command_value, label in cases:
            with self.subTest(label=label):
                data = {
                    "unit_name": "test",
                    "is_user_unit": False,
                    "action": "lock",
                    "amount": 10,
                    "unit": "seconds",
                    "command": command_value,
                }
                record = ScheduledJobRecord.from_json_dict(data)
                self.assertIsNone(record.command)

    def test_from_json_dict_ignores_extra_fields(self) -> None:
        record = ScheduledJobRecord.from_json_dict(
            {
                "unit_name": "test",
                "is_user_unit": False,
                "action": "lock",
                "amount": 10,
                "unit": "seconds",
                "extra_field": "should be ignored",
            }
        )
        self.assertEqual(record.unit_name, "test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
