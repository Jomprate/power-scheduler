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

    def test_save_current_job_validations(self) -> None:
        cases = [
            (
                ScheduledJobRecord(
                    unit_name="",
                    is_user_unit=True,
                    action=PowerAction.LOCK,
                    amount=10,
                    unit=TimeUnit.SECONDS,
                ),
                "unit_name cannot be empty",
                "empty unit_name",
            ),
            (
                ScheduledJobRecord(
                    unit_name="test",
                    is_user_unit=True,
                    action=PowerAction.LOCK,
                    amount=0,
                    unit=TimeUnit.SECONDS,
                ),
                "amount must be greater than zero",
                "non-positive amount",
            ),
        ]

        for record, msg, label in cases:
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, msg):
                self.repo.save_current_job(record)

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
