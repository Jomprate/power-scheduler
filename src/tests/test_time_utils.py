from __future__ import annotations

import unittest

from domain.enums import TimeUnit
from utils.time_utils import format_human_time, to_seconds


class ToSecondsTests(unittest.TestCase):
    def test_seconds(self) -> None:
        self.assertEqual(to_seconds(15, TimeUnit.SECONDS), 15)

    def test_minutes(self) -> None:
        self.assertEqual(to_seconds(3, TimeUnit.MINUTES), 180)

    def test_hours(self) -> None:
        self.assertEqual(to_seconds(2, TimeUnit.HOURS), 7200)

    def test_zero_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            to_seconds(0, TimeUnit.SECONDS)

    def test_negative_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            to_seconds(-5, TimeUnit.MINUTES)

    def test_unsupported_unit_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported time unit"):
            to_seconds(1, "days")  # type: ignore[arg-type]


class FormatHumanTimeTests(unittest.TestCase):
    def test_seconds_plural(self) -> None:
        self.assertEqual(format_human_time(15, TimeUnit.SECONDS), "15 seconds")

    def test_seconds_singular(self) -> None:
        self.assertEqual(format_human_time(1, TimeUnit.SECONDS), "1 second")

    def test_minutes_plural(self) -> None:
        self.assertEqual(format_human_time(3, TimeUnit.MINUTES), "3 minutes")

    def test_minutes_singular(self) -> None:
        self.assertEqual(format_human_time(1, TimeUnit.MINUTES), "1 minute")

    def test_hours_plural(self) -> None:
        self.assertEqual(format_human_time(2, TimeUnit.HOURS), "2 hours")

    def test_hours_singular(self) -> None:
        self.assertEqual(format_human_time(1, TimeUnit.HOURS), "1 hour")

    def test_unsupported_unit_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported time unit"):
            format_human_time(1, "months")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
