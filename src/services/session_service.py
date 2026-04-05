from __future__ import annotations

import os
import shutil
from typing import Final

from domain.enums import PowerAction


class SessionService:
    """
    Handles only session-level actions.

    Responsibility:
    - identify whether an action belongs to the session domain
    - return the concrete command for supported session actions

    It does NOT:
    - schedule actions
    - cancel actions
    - handle system power actions like suspend, hibernate or power off
    """

    SUPPORTED_ACTIONS: Final[set[PowerAction]] = {
        PowerAction.LOCK,
        PowerAction.LOG_OUT,
    }

    def supports(self, action: PowerAction) -> bool:
        return action in self.SUPPORTED_ACTIONS

    def build_action_command(self, action: PowerAction) -> list[str]:
        if action == PowerAction.LOCK:
            return self._build_lock_command()

        if action == PowerAction.LOG_OUT:
            return self._build_logout_command()

        raise ValueError(
            f"Unsupported session action for SessionService: {action}"
        )

    def _build_lock_command(self) -> list[str]:
        session_id = self._get_session_id()

        loginctl_path = self._which_required("loginctl")

        if session_id:
            return [loginctl_path, "lock-session", session_id]

        # Fallback only if session id is unavailable.
        # This still targets the caller session when supported by logind.
        return [loginctl_path, "lock-session"]

    def _build_logout_command(self) -> list[str]:
        gnome_session_quit_path = shutil.which("gnome-session-quit")
        if gnome_session_quit_path:
            return [
                gnome_session_quit_path,
                "--logout",
                "--no-prompt",
            ]

        session_id = self._get_session_id()
        if not session_id:
            raise RuntimeError(
                "Unable to determine the current session id for log out action."
            )

        loginctl_path = self._which_required("loginctl")
        return [loginctl_path, "terminate-session", session_id]

    @staticmethod
    def _get_session_id() -> str | None:
        session_id = os.environ.get("XDG_SESSION_ID", "").strip()
        return session_id or None

    @staticmethod
    def _which_required(binary_name: str) -> str:
        resolved = shutil.which(binary_name)
        if not resolved:
            raise RuntimeError(f"Required binary not found: {binary_name}")
        return resolved