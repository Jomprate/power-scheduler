from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.capability_service import CapabilityService


class CapabilityServiceTests(unittest.TestCase):
    @patch("services.capability_service.shutil.which")
    def test_has_required_commands_returns_true_when_all_exist(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            mapping = {
                "systemd-run": "/usr/bin/systemd-run",
                "systemctl": "/usr/bin/systemctl",
                "loginctl": "/usr/bin/loginctl",
            }
            return mapping.get(binary_name)

        mock_which.side_effect = which_side_effect

        self.assertTrue(CapabilityService.has_required_commands())

    @patch("services.capability_service.shutil.which")
    def test_has_required_commands_returns_false_when_one_is_missing(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            mapping = {
                "systemd-run": "/usr/bin/systemd-run",
                "systemctl": None,
                "loginctl": "/usr/bin/loginctl",
            }
            return mapping.get(binary_name)

        mock_which.side_effect = which_side_effect

        self.assertFalse(CapabilityService.has_required_commands())

    @patch("services.capability_service.shutil.which", return_value="/usr/bin/systemd-run")
    def test_get_schedule_capability_returns_available_when_systemd_run_exists(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_schedule_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "schedule")
        self.assertIn("systemd-run", capability.reason)

    @patch("services.capability_service.shutil.which", return_value=None)
    def test_get_schedule_capability_returns_unavailable_when_systemd_run_missing(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_schedule_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "schedule")
        self.assertIn("was not found", capability.reason)

    @patch("services.capability_service.shutil.which")
    def test_get_lock_capability_returns_available_when_loginctl_exists(
        self,
        mock_which,
    ) -> None:
        mock_which.side_effect = lambda binary_name: (
            "/usr/bin/loginctl" if binary_name == "loginctl" else None
        )

        capability = CapabilityService.get_lock_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "lock")
        self.assertIn("loginctl", capability.reason)

    @patch("services.capability_service.shutil.which", return_value=None)
    def test_get_lock_capability_returns_unavailable_when_loginctl_missing(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_lock_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "lock")

    @patch("services.capability_service.shutil.which")
    def test_get_logout_capability_prefers_gnome_session_quit_when_available(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            mapping = {
                "gnome-session-quit": "/usr/bin/gnome-session-quit",
                "loginctl": "/usr/bin/loginctl",
            }
            return mapping.get(binary_name)

        mock_which.side_effect = which_side_effect

        capability = CapabilityService.get_logout_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "log_out")
        self.assertIn("gnome-session-quit", capability.reason)

    @patch("services.capability_service.shutil.which")
    def test_get_logout_capability_uses_loginctl_fallback_when_gnome_missing(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            mapping = {
                "gnome-session-quit": None,
                "loginctl": "/usr/bin/loginctl",
            }
            return mapping.get(binary_name)

        mock_which.side_effect = which_side_effect

        capability = CapabilityService.get_logout_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "log_out")
        self.assertIn("terminate-session fallback", capability.reason)

    @patch("services.capability_service.shutil.which", return_value=None)
    def test_get_logout_capability_returns_unavailable_when_no_binary_exists(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_logout_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "log_out")

    @patch("services.capability_service.shutil.which")
    @patch.object(CapabilityService, "_kernel_supports_suspend", return_value=True)
    def test_get_suspend_capability_returns_available_when_binary_and_kernel_support_exist(
        self,
        _mock_kernel_supports_suspend,
        mock_which,
    ) -> None:
        mock_which.side_effect = lambda binary_name: (
            "/usr/bin/systemctl" if binary_name == "systemctl" else None
        )

        capability = CapabilityService.get_suspend_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "suspend")
        self.assertIn("indicate suspend support", capability.reason)

    @patch("services.capability_service.shutil.which")
    @patch.object(CapabilityService, "_kernel_supports_suspend", return_value=False)
    def test_get_suspend_capability_returns_unavailable_when_kernel_support_is_missing(
        self,
        _mock_kernel_supports_suspend,
        mock_which,
    ) -> None:
        mock_which.side_effect = lambda binary_name: (
            "/usr/bin/systemctl" if binary_name == "systemctl" else None
        )

        capability = CapabilityService.get_suspend_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "suspend")

    @patch("services.capability_service.shutil.which", return_value=None)
    def test_get_suspend_capability_returns_unavailable_when_systemctl_missing(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_suspend_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "suspend")

    @patch("services.capability_service.shutil.which")
    @patch.object(CapabilityService, "_kernel_supports_hibernate", return_value=True)
    def test_get_hibernate_capability_returns_available_when_binary_and_kernel_support_exist(
        self,
        _mock_kernel_supports_hibernate,
        mock_which,
    ) -> None:
        mock_which.side_effect = lambda binary_name: (
            "/usr/bin/systemctl" if binary_name == "systemctl" else None
        )

        capability = CapabilityService.get_hibernate_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "hibernate")
        self.assertIn("indicate hibernate support", capability.reason)

    @patch("services.capability_service.shutil.which")
    @patch.object(CapabilityService, "_kernel_supports_hibernate", return_value=False)
    def test_get_hibernate_capability_returns_unavailable_when_kernel_support_is_missing(
        self,
        _mock_kernel_supports_hibernate,
        mock_which,
    ) -> None:
        mock_which.side_effect = lambda binary_name: (
            "/usr/bin/systemctl" if binary_name == "systemctl" else None
        )

        capability = CapabilityService.get_hibernate_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "hibernate")

    @patch("services.capability_service.shutil.which", return_value=None)
    def test_get_hibernate_capability_returns_unavailable_when_systemctl_missing(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_hibernate_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "hibernate")

    @patch("services.capability_service.shutil.which")
    def test_get_power_off_capability_returns_available_when_systemctl_exists(
        self,
        mock_which,
    ) -> None:
        mock_which.side_effect = lambda binary_name: (
            "/usr/bin/systemctl" if binary_name == "systemctl" else None
        )

        capability = CapabilityService.get_power_off_capability()

        self.assertTrue(capability.available)
        self.assertEqual(capability.action_key, "power_off")

    @patch("services.capability_service.shutil.which", return_value=None)
    def test_get_power_off_capability_returns_unavailable_when_systemctl_missing(
        self,
        _mock_which,
    ) -> None:
        capability = CapabilityService.get_power_off_capability()

        self.assertFalse(capability.available)
        self.assertEqual(capability.action_key, "power_off")

    @patch.object(CapabilityService, "_read_text_if_exists")
    def test_kernel_supports_suspend_returns_true_for_mem_state(
        self,
        mock_read_text,
    ) -> None:
        mock_read_text.return_value = "freeze mem disk"

        self.assertTrue(CapabilityService._kernel_supports_suspend())

    @patch.object(CapabilityService, "_read_text_if_exists")
    def test_kernel_supports_suspend_returns_false_when_no_suspend_state_exists(
        self,
        mock_read_text,
    ) -> None:
        mock_read_text.return_value = "disk"

        self.assertFalse(CapabilityService._kernel_supports_suspend())

    @patch.object(CapabilityService, "_read_text_if_exists")
    def test_kernel_supports_hibernate_returns_true_when_disk_state_and_disk_modes_exist(
        self,
        mock_read_text,
    ) -> None:
        def read_side_effect(path: Path) -> str:
            if path == CapabilityService.SYS_POWER_STATE_PATH:
                return "freeze mem disk"
            if path == CapabilityService.SYS_POWER_DISK_PATH:
                return "[shutdown] reboot suspend test_resume"
            return ""

        mock_read_text.side_effect = read_side_effect

        self.assertTrue(CapabilityService._kernel_supports_hibernate())

    @patch.object(CapabilityService, "_read_text_if_exists")
    def test_kernel_supports_hibernate_returns_false_when_disk_state_is_missing(
        self,
        mock_read_text,
    ) -> None:
        def read_side_effect(path: Path) -> str:
            if path == CapabilityService.SYS_POWER_STATE_PATH:
                return "freeze mem"
            if path == CapabilityService.SYS_POWER_DISK_PATH:
                return "[shutdown] reboot"
            return ""

        mock_read_text.side_effect = read_side_effect

        self.assertFalse(CapabilityService._kernel_supports_hibernate())

    @patch.object(CapabilityService, "_read_text_if_exists")
    def test_kernel_supports_hibernate_returns_false_when_disk_modes_are_missing(
        self,
        mock_read_text,
    ) -> None:
        def read_side_effect(path: Path) -> str:
            if path == CapabilityService.SYS_POWER_STATE_PATH:
                return "freeze mem disk"
            if path == CapabilityService.SYS_POWER_DISK_PATH:
                return ""
            return ""

        mock_read_text.side_effect = read_side_effect

        self.assertFalse(CapabilityService._kernel_supports_hibernate())

    @patch("services.capability_service.Path.exists", return_value=False)
    def test_read_text_if_exists_returns_empty_string_when_path_does_not_exist(
        self,
        _mock_exists,
    ) -> None:
        result = CapabilityService._read_text_if_exists(Path("/fake/path"))

        self.assertEqual(result, "")

    @patch("services.capability_service.Path.read_text", side_effect=OSError("boom"))
    @patch("services.capability_service.Path.exists", return_value=True)
    def test_read_text_if_exists_returns_empty_string_on_os_error(
        self,
        _mock_exists,
        _mock_read_text,
    ) -> None:
        result = CapabilityService._read_text_if_exists(Path("/fake/path"))

        self.assertEqual(result, "")

    @patch("services.capability_service.Path.read_text", return_value="  freeze mem disk  \n")
    @patch("services.capability_service.Path.exists", return_value=True)
    def test_read_text_if_exists_returns_trimmed_content(
        self,
        _mock_exists,
        _mock_read_text,
    ) -> None:
        result = CapabilityService._read_text_if_exists(Path("/fake/path"))

        self.assertEqual(result, "freeze mem disk")

    @patch.object(CapabilityService, "get_hibernate_capability")
    def test_can_hibernate_returns_boolean_from_capability(
        self,
        mock_get_hibernate_capability,
    ) -> None:
        mock_get_hibernate_capability.return_value.available = True

        self.assertTrue(CapabilityService.can_hibernate())

    @patch.object(CapabilityService, "get_capabilities")
    def test_get_capabilities_returns_expected_keys(
        self,
        mock_get_capabilities,
    ) -> None:
        mock_get_capabilities.return_value = {
            "lock": object(),
            "log_out": object(),
            "suspend": object(),
            "hibernate": object(),
            "power_off": object(),
            "schedule": object(),
        }

        result = CapabilityService.get_capabilities()

        self.assertEqual(
            set(result.keys()),
            {"lock", "log_out", "suspend", "hibernate", "power_off", "schedule"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)