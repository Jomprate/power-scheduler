from __future__ import annotations

import shutil
from typing import Final

from domain.enums import PowerAction


class ShutdownService:
    """
    Handles only system-level power actions.

    Responsibility:
    - identify whether an action belongs to the shutdown/power domain
    - return the concrete command for supported system power actions

    It does NOT:
    - schedule actions
    - cancel actions
    - handle session actions like lock or log out
    """

    SUPPORTED_ACTIONS: Final[set[PowerAction]] = {
        PowerAction.SUSPEND,
        PowerAction.HIBERNATE,
        PowerAction.POWER_OFF,
    }

    def supports(self, action: PowerAction) -> bool:
        return action in self.SUPPORTED_ACTIONS

    def build_action_command(self, action: PowerAction) -> list[str]:
        systemctl_path = self._which_required("systemctl")

        if action == PowerAction.SUSPEND:
            return self._build_suspend_command(systemctl_path)

        if action == PowerAction.HIBERNATE:
            return self._build_hibernate_command(systemctl_path)

        if action == PowerAction.POWER_OFF:
            return self._build_poweroff_command(systemctl_path)

        raise ValueError(
            f"Unsupported shutdown action for ShutdownService: {action}"
        )

    @staticmethod
    def _build_suspend_command(systemctl_path: str) -> list[str]:
        return [systemctl_path, "start", "suspend.target"]

    @staticmethod
    def _build_hibernate_command(systemctl_path: str) -> list[str]:
        return [systemctl_path, "start", "hibernate.target"]

    @staticmethod
    def _build_poweroff_command(systemctl_path: str) -> list[str]:
        return [systemctl_path, "start", "poweroff.target"]

    @staticmethod
    def _which_required(binary_name: str) -> str:
        resolved = shutil.which(binary_name)
        if not resolved:
            raise RuntimeError(f"Required binary not found: {binary_name}")
        return resolved