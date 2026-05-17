from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.capability_service import (
    CapabilityService,
    HostSystemProbe,
)


class CapabilityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_probe = Mock()
        self.service = CapabilityService(probe=self.mock_probe)

    def test_get_schedule_capability_returns_available_when_systemd_run_exists(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemd-run"

        capability = self.service.get_schedule_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "schedule")
        self.assertIn("systemd-run", capability.reason)

    def test_get_schedule_capability_returns_unavailable_when_systemd_run_missing(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = None

        capability = self.service.get_schedule_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "schedule")
        self.assertIn("was not found", capability.reason)

    def test_get_lock_capability_returns_available_when_loginctl_exists(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/loginctl"

        capability = self.service.get_lock_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "lock")
        self.assertIn("loginctl", capability.reason)

    def test_get_lock_capability_returns_unavailable_when_loginctl_missing(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = None

        capability = self.service.get_lock_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "lock")

    def test_get_logout_capability_prefers_gnome_session_quit_when_available(
        self,
    ) -> None:
        def find_binary(name: str) -> str | None:
            mapping = {
                "gnome-session-quit": "/usr/bin/gnome-session-quit",
                "loginctl": "/usr/bin/loginctl",
            }
            return mapping.get(name)

        self.mock_probe.find_binary.side_effect = find_binary

        capability = self.service.get_logout_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "log_out")
        self.assertIn("gnome-session-quit", capability.reason)

    def test_get_logout_capability_uses_loginctl_fallback_when_gnome_missing(
        self,
    ) -> None:
        def find_binary(name: str) -> str | None:
            mapping = {
                "gnome-session-quit": None,
                "loginctl": "/usr/bin/loginctl",
            }
            return mapping.get(name)

        self.mock_probe.find_binary.side_effect = find_binary

        capability = self.service.get_logout_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "log_out")
        self.assertIn("terminate-session fallback", capability.reason)

    def test_get_logout_capability_returns_unavailable_when_no_binary_exists(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = None

        capability = self.service.get_logout_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "log_out")

    def test_get_suspend_capability_returns_available_when_binary_and_kernel_support_exist(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemctl"
        self.mock_probe.read_text_file.return_value = "freeze mem disk"

        capability = self.service.get_suspend_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "suspend")
        self.assertIn("indicate suspend support", capability.reason)

    def test_get_suspend_capability_returns_unavailable_when_kernel_support_is_missing(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemctl"
        self.mock_probe.read_text_file.return_value = "disk"

        capability = self.service.get_suspend_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "suspend")

    def test_get_suspend_capability_returns_unavailable_when_systemctl_missing(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = None

        capability = self.service.get_suspend_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "suspend")

    def test_get_hibernate_capability_returns_available_when_binary_and_kernel_support_exist(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemctl"
        self.mock_probe.read_text_file.side_effect = lambda path: (
            "freeze mem disk"
            if "state" in str(path)
            else "[shutdown] reboot suspend test_resume"
            if "disk" in str(path)
            else ""
        )

        capability = self.service.get_hibernate_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "hibernate")
        self.assertIn("indicate hibernate support", capability.reason)

    def test_get_hibernate_capability_returns_unavailable_when_kernel_support_is_missing(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemctl"
        self.mock_probe.read_text_file.side_effect = lambda path: (
            "freeze mem"
            if "state" in str(path)
            else "[shutdown] reboot"
            if "disk" in str(path)
            else ""
        )

        capability = self.service.get_hibernate_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "hibernate")

    def test_get_power_off_capability_returns_available_when_systemctl_exists(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemctl"

        capability = self.service.get_power_off_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "power_off")

    def test_get_power_off_capability_returns_unavailable_when_systemctl_missing(
        self,
    ) -> None:
        self.mock_probe.find_binary.return_value = None

        capability = self.service.get_power_off_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "power_off")

    def test_get_capabilities_returns_expected_keys(self) -> None:
        self.mock_probe.find_binary.return_value = "/usr/bin/systemctl"
        self.mock_probe.read_text_file.return_value = "freeze mem disk"

        result = self.service.get_capabilities()

        self.assertEqual(
            set(result.keys()),
            {"lock", "log_out", "suspend", "hibernate", "power_off", "schedule"},
        )


class HostSystemProbeTests(unittest.TestCase):
    def test_find_binary_returns_none_when_not_found(self) -> None:
        probe = HostSystemProbe()
        result = probe.find_binary("this-binary-does-not-exist-12345xyz")
        self.assertIsNone(result)

    def test_read_text_file_returns_empty_string_when_path_does_not_exist(
        self,
    ) -> None:
        probe = HostSystemProbe()
        result = probe.read_text_file(Path("/fake/nonexistent/path"))
        self.assertEqual(result, "")

    @patch(
        "services.capability_service.Path.read_text",
        return_value="  freeze mem disk  \n",
    )
    @patch("services.capability_service.Path.exists", return_value=True)
    def test_read_text_file_returns_trimmed_content(
        self,
        _mock_exists,
        _mock_read_text,
    ) -> None:
        probe = HostSystemProbe()
        result = probe.read_text_file(Path("/fake/path"))
        self.assertEqual(result, "freeze mem disk")

    @patch("services.capability_service.Path.read_text", side_effect=OSError("boom"))
    @patch("services.capability_service.Path.exists", return_value=True)
    def test_read_text_file_returns_empty_string_on_os_error(
        self,
        _mock_exists,
        _mock_read_text,
    ) -> None:
        probe = HostSystemProbe()
        result = probe.read_text_file(Path("/fake/path"))
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
