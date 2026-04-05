from __future__ import annotations

import unittest
from unittest.mock import patch

from domain.enums import PowerAction
from services.session_service import SessionService


class SessionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SessionService()

    def test_supports_returns_true_for_session_actions(self) -> None:
        self.assertTrue(
            self.service.supports(PowerAction.LOCK),
            "LOCK should be supported by SessionService.",
        )
        self.assertTrue(
            self.service.supports(PowerAction.LOG_OUT),
            "LOG_OUT should be supported by SessionService.",
        )

    def test_supports_returns_false_for_non_session_actions(self) -> None:
        self.assertFalse(
            self.service.supports(PowerAction.SUSPEND),
            "SUSPEND should not be supported by SessionService.",
        )
        self.assertFalse(
            self.service.supports(PowerAction.HIBERNATE),
            "HIBERNATE should not be supported by SessionService.",
        )
        self.assertFalse(
            self.service.supports(PowerAction.POWER_OFF),
            "POWER_OFF should not be supported by SessionService.",
        )

    @patch.dict("os.environ", {"XDG_SESSION_ID": "42"}, clear=False)
    @patch("services.session_service.shutil.which")
    def test_lock_uses_loginctl_with_current_session_id(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "loginctl":
                return "/usr/bin/loginctl"
            return None

        mock_which.side_effect = which_side_effect

        command = self.service.build_action_command(PowerAction.LOCK)

        self.assertEqual(
            command,
            ["/usr/bin/loginctl", "lock-session", "42"],
            "LOCK should use loginctl lock-session with the current XDG session id.",
        )

    @patch.dict("os.environ", {}, clear=True)
    @patch("services.session_service.shutil.which")
    def test_lock_falls_back_to_loginctl_without_session_id(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "loginctl":
                return "/usr/bin/loginctl"
            return None

        mock_which.side_effect = which_side_effect

        command = self.service.build_action_command(PowerAction.LOCK)

        self.assertEqual(
            command,
            ["/usr/bin/loginctl", "lock-session"],
            "LOCK should fall back to loginctl lock-session when XDG_SESSION_ID is unavailable.",
        )

    @patch.dict("os.environ", {"XDG_SESSION_ID": "42"}, clear=False)
    @patch("services.session_service.shutil.which", return_value=None)
    def test_lock_raises_when_loginctl_is_missing(
        self,
        _mock_which,
    ) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "Unable to resolve a supported lock command",
        ):
            self.service.build_action_command(PowerAction.LOCK)

    @patch.dict("os.environ", {"XDG_SESSION_ID": "42"}, clear=False)
    @patch("services.session_service.shutil.which")
    def test_logout_prefers_gnome_session_quit_when_available(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "gnome-session-quit":
                return "/usr/bin/gnome-session-quit"
            if binary_name == "loginctl":
                return "/usr/bin/loginctl"
            return None

        mock_which.side_effect = which_side_effect

        command = self.service.build_action_command(PowerAction.LOG_OUT)

        self.assertEqual(
            command,
            [
                "/usr/bin/gnome-session-quit",
                "--logout",
                "--no-prompt",
            ],
            "LOG_OUT should prefer gnome-session-quit when that binary is available.",
        )

    @patch.dict("os.environ", {"XDG_SESSION_ID": "42"}, clear=False)
    @patch("services.session_service.shutil.which")
    def test_logout_falls_back_to_loginctl_terminate_session(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "gnome-session-quit":
                return None
            if binary_name == "loginctl":
                return "/usr/bin/loginctl"
            return None

        mock_which.side_effect = which_side_effect

        command = self.service.build_action_command(PowerAction.LOG_OUT)

        self.assertEqual(
            command,
            ["/usr/bin/loginctl", "terminate-session", "42"],
            "LOG_OUT should fall back to loginctl terminate-session with the current XDG session id.",
        )

    @patch.dict("os.environ", {}, clear=True)
    @patch("services.session_service.shutil.which")
    def test_logout_raises_when_no_supported_command_can_be_resolved(
        self,
        mock_which,
    ) -> None:
        def which_side_effect(binary_name: str) -> str | None:
            if binary_name == "gnome-session-quit":
                return None
            if binary_name == "loginctl":
                return "/usr/bin/loginctl"
            return None

        mock_which.side_effect = which_side_effect

        with self.assertRaisesRegex(
            RuntimeError,
            "Unable to determine the current session id",
        ):
            self.service.build_action_command(PowerAction.LOG_OUT)

    def test_build_action_command_raises_for_unsupported_action(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported session action",
        ):
            self.service.build_action_command(PowerAction.SUSPEND)


if __name__ == "__main__":
    unittest.main(verbosity=2)