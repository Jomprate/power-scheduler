from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.capability_service import CapabilityService, HostSystemProbe


class CapabilityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = Mock(spec=HostSystemProbe)
        self.service = CapabilityService(probe=self.probe)

    def test_get_schedule_capability_found(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemd-run"
        cap = self.service.get_schedule_capability()
        self.assertTrue(cap.available)
        self.assertIn("systemd-run", cap.reason)

    def test_get_schedule_capability_not_found(self) -> None:
        self.probe.find_binary.return_value = None
        cap = self.service.get_schedule_capability()
        self.assertFalse(cap.available)
        self.assertIn("not found", cap.reason)

    def test_get_lock_capability_found(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/loginctl"
        cap = self.service.get_lock_capability()
        self.assertTrue(cap.available)
        self.assertIn("loginctl", cap.reason)

    def test_get_lock_capability_not_found(self) -> None:
        self.probe.find_binary.return_value = None
        cap = self.service.get_lock_capability()
        self.assertFalse(cap.available)
        self.assertIn("not found", cap.reason)

    def test_get_logout_capability_gnome_session_quit(self) -> None:
        self.probe.find_binary.side_effect = lambda name: (
            "/usr/bin/gnome-session-quit" if name == "gnome-session-quit" else None
        )
        cap = self.service.get_logout_capability()
        self.assertTrue(cap.available)
        self.assertIn("gnome-session-quit", cap.reason)

    def test_get_logout_capability_loginctl_with_session(self) -> None:
        self.probe.find_binary.side_effect = lambda name: (
            "/usr/bin/loginctl" if name == "loginctl" else None
        )
        with patch.dict(os.environ, {"XDG_SESSION_ID": "42"}, clear=True):
            cap = self.service.get_logout_capability()
        self.assertTrue(cap.available)
        self.assertIn("loginctl", cap.reason)

    def test_get_logout_capability_loginctl_without_session(self) -> None:
        self.probe.find_binary.side_effect = lambda name: (
            "/usr/bin/loginctl" if name == "loginctl" else None
        )
        with patch.dict(os.environ, {}, clear=True):
            cap = self.service.get_logout_capability()
        self.assertFalse(cap.available)
        self.assertIn("XDG_SESSION_ID", cap.reason)

    def test_get_logout_capability_none_found(self) -> None:
        self.probe.find_binary.return_value = None
        cap = self.service.get_logout_capability()
        self.assertFalse(cap.available)
        self.assertIn("Neither", cap.reason)

    def test_get_suspend_capability_available(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemctl"
        self.probe.read_text_file.side_effect = lambda path: (
            "mem freeze standby" if path == Path("/sys/power/state") else ""
        )
        cap = self.service.get_suspend_capability()
        self.assertTrue(cap.available)
        self.assertIn("systemctl", cap.reason)

    def test_get_suspend_capability_no_kernel_support(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemctl"
        self.probe.read_text_file.return_value = ""
        cap = self.service.get_suspend_capability()
        self.assertFalse(cap.available)
        self.assertIn("kernel", cap.reason)

    def test_get_hibernate_capability_available(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemctl"
        self.probe.read_text_file.side_effect = lambda path: (
            "disk" if path == Path("/sys/power/state") else "reboot"
        )
        cap = self.service.get_hibernate_capability()
        self.assertTrue(cap.available)
        self.assertIn("systemctl", cap.reason)

    def test_get_hibernate_capability_no_kernel_support(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemctl"
        self.probe.read_text_file.return_value = ""
        cap = self.service.get_hibernate_capability()
        self.assertFalse(cap.available)
        self.assertIn("kernel", cap.reason)

    def test_get_power_off_capability_found(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemctl"
        cap = self.service.get_power_off_capability()
        self.assertTrue(cap.available)
        self.assertIn("systemctl", cap.reason)

    def test_get_power_off_capability_not_found(self) -> None:
        self.probe.find_binary.return_value = None
        cap = self.service.get_power_off_capability()
        self.assertFalse(cap.available)
        self.assertIn("not found", cap.reason)

    def test_get_capabilities_returns_all_keys(self) -> None:
        self.probe.find_binary.return_value = "/usr/bin/systemctl"
        self.probe.read_text_file.return_value = "mem disk"
        caps = self.service.get_capabilities()
        self.assertEqual(
            set(caps.keys()),
            {"lock", "log_out", "suspend", "hibernate", "power_off", "schedule"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
