from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.capability_service import HostSystemProbe


class HostSystemProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = HostSystemProbe()

    def test_find_binary_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/systemctl"):
            result = self.probe.find_binary("systemctl")
            self.assertEqual(result, "/usr/bin/systemctl")

    def test_find_binary_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            result = self.probe.find_binary("nonexistent")
            self.assertIsNone(result)

    def test_read_text_file_exists(self) -> None:
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path, "read_text", return_value="hello world"
        ):
            result = self.probe.read_text_file(Path("/tmp/test.txt"))
            self.assertEqual(result, "hello world")

    def test_read_text_file_not_exists(self) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = self.probe.read_text_file(Path("/tmp/missing.txt"))
            self.assertEqual(result, "")

    def test_read_text_file_os_error(self) -> None:
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path, "read_text", side_effect=OSError("permission denied")
        ):
            result = self.probe.read_text_file(Path("/tmp/error.txt"))
            self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
