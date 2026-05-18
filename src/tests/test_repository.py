from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from domain.enums import PowerAction, TimeUnit
from repositories.scheduled_job_repository import (
    ScheduledJobRecord,
    ScheduledJobRepository,
)


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

    def _assert_from_json_raises(self, data: dict, msg: str | None = None) -> None:
        if msg:
            with self.assertRaisesRegex(ValueError, msg):
                ScheduledJobRecord.from_json_dict(data)
        else:
            with self.assertRaises(ValueError):
                ScheduledJobRecord.from_json_dict(data)

    def _assert_from_json_command_none(self, data: dict) -> None:
        record = ScheduledJobRecord.from_json_dict(data)
        self.assertIsNone(record.command)

    def test_from_json_dict_raises_for_missing_unit_name(self) -> None:
        self._assert_from_json_raises(
            {
                "unit_name": "",
                "is_user_unit": False,
                "action": "lock",
                "amount": 10,
                "unit": "seconds",
            }
        )

    def test_from_json_dict_raises_for_non_positive_amount(self) -> None:
        self._assert_from_json_raises(
            {
                "unit_name": "test",
                "is_user_unit": False,
                "action": "lock",
                "amount": 0,
                "unit": "seconds",
            },
            "greater than zero",
        )

    def test_from_json_dict_raises_for_bool_amount(self) -> None:
        self._assert_from_json_raises(
            {
                "unit_name": "test",
                "is_user_unit": False,
                "action": "lock",
                "amount": True,
                "unit": "seconds",
            },
            "not a boolean",
        )

    def test_from_json_dict_accepts_null_command(self) -> None:
        self._assert_from_json_command_none(
            {
                "unit_name": "test",
                "is_user_unit": False,
                "action": "lock",
                "amount": 10,
                "unit": "seconds",
                "command": None,
            }
        )

    def test_from_json_dict_accepts_empty_command_as_none(self) -> None:
        self._assert_from_json_command_none(
            {
                "unit_name": "test",
                "is_user_unit": False,
                "action": "lock",
                "amount": 10,
                "unit": "seconds",
                "command": "   ",
            }
        )

    def test_from_json_dict_raises_for_unknown_action_value(self) -> None:
        self._assert_from_json_raises(
            {
                "unit_name": "test",
                "is_user_unit": False,
                "action": "unknown_action",
                "amount": 10,
                "unit": "seconds",
            }
        )

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


class ScheduledJobRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.storage_file = Path(self._tmp_dir.name) / "current_job.json"
        self.repo = ScheduledJobRepository(storage_file=self.storage_file)

    def tearDown(self) -> None:
        self._tmp_dir.cleanup()

    def test_storage_file_property(self) -> None:
        self.assertEqual(self.repo.storage_file, self.storage_file)

    def test_save_and_get_current_job(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-lock-test",
            is_user_unit=True,
            action=PowerAction.LOCK,
            amount=10,
            unit=TimeUnit.SECONDS,
            command="/usr/bin/loginctl lock-session 42",
        )

        self.repo.save_current_job(record)
        restored = self.repo.get_current_job()

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.unit_name, record.unit_name)
        self.assertEqual(restored.is_user_unit, record.is_user_unit)
        self.assertEqual(restored.action, record.action)
        self.assertEqual(restored.amount, record.amount)
        self.assertEqual(restored.unit, record.unit)
        self.assertEqual(restored.command, record.command)
        self.assertIsNotNone(restored.created_at)
        assert restored.created_at is not None

    def test_get_current_job_returns_none_when_no_file(self) -> None:
        result = self.repo.get_current_job()
        self.assertIsNone(result)

    def test_get_current_job_returns_none_for_corrupt_file(self) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.storage_file.write_text("{ invalid json ", encoding="utf-8")
        result = self.repo.get_current_job()
        self.assertIsNone(result)

    def test_get_current_job_returns_none_for_empty_file(self) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.storage_file.write_text("", encoding="utf-8")
        result = self.repo.get_current_job()
        self.assertIsNone(result)

    def test_clear_current_job_removes_file(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-suspend-test",
            is_user_unit=False,
            action=PowerAction.SUSPEND,
            amount=5,
            unit=TimeUnit.MINUTES,
        )
        self.repo.save_current_job(record)
        self.assertTrue(self.storage_file.exists())

        self.repo.clear_current_job()
        self.assertFalse(self.storage_file.exists())

    def test_clear_current_job_does_not_raise_when_no_file(self) -> None:
        self.repo.clear_current_job()

    def test_has_current_job_returns_true_when_job_exists(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-test",
            is_user_unit=True,
            action=PowerAction.LOCK,
            amount=1,
            unit=TimeUnit.SECONDS,
        )
        self.repo.save_current_job(record)
        self.assertTrue(self.repo.has_current_job())

    def test_has_current_job_returns_false_when_no_job(self) -> None:
        self.assertFalse(self.repo.has_current_job())

    def test_has_current_job_returns_false_for_empty_file(self) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.storage_file.write_text("", encoding="utf-8")
        self.assertFalse(self.repo.has_current_job())

    def test_save_current_job_preserves_existing_timestamp(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-test",
            is_user_unit=False,
            action=PowerAction.SUSPEND,
            amount=10,
            unit=TimeUnit.MINUTES,
            created_at="2025-01-01T00:00:00+00:00",
        )
        self.repo.save_current_job(record)

        raw = self.storage_file.read_text(encoding="utf-8")
        payload = json.loads(raw)
        self.assertEqual(payload["created_at"], "2025-01-01T00:00:00+00:00")

    def _assert_save_raises(self, record: ScheduledJobRecord, msg: str) -> None:
        with self.assertRaisesRegex(ValueError, msg):
            self.repo.save_current_job(record)

    def test_save_current_job_raises_for_empty_unit_name(self) -> None:
        self._assert_save_raises(
            ScheduledJobRecord(
                unit_name="",
                is_user_unit=True,
                action=PowerAction.LOCK,
                amount=10,
                unit=TimeUnit.SECONDS,
            ),
            "unit_name cannot be empty",
        )

    def test_save_current_job_raises_for_non_positive_amount(self) -> None:
        self._assert_save_raises(
            ScheduledJobRecord(
                unit_name="test",
                is_user_unit=True,
                action=PowerAction.LOCK,
                amount=0,
                unit=TimeUnit.SECONDS,
            ),
            "amount must be greater than zero",
        )

    def test_json_file_is_valid_json(self) -> None:
        record = ScheduledJobRecord(
            unit_name="power-scheduler-lock-test",
            is_user_unit=True,
            action=PowerAction.LOCK,
            amount=10,
            unit=TimeUnit.SECONDS,
        )
        self.repo.save_current_job(record)

        raw = self.storage_file.read_text(encoding="utf-8")
        payload = json.loads(raw)
        self.assertEqual(payload["unit_name"], "power-scheduler-lock-test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
