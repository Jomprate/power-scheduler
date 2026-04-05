from __future__ import annotations

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
        if action == PowerAction.SUSPEND:
            return self._build_suspend_command()

        if action == PowerAction.HIBERNATE:
            return self._build_hibernate_command()

        if action == PowerAction.POWER_OFF:
            return self._build_poweroff_command()

        raise ValueError(
            f"Unsupported shutdown action for ShutdownService: {action}"
        )

    @staticmethod
    def _build_suspend_command() -> list[str]:
        return ["systemctl", "suspend"]

    @staticmethod
    def _build_hibernate_command() -> list[str]:
        return ["systemctl", "hibernate"]

    @staticmethod
    def _build_poweroff_command() -> list[str]:
        return ["systemctl", "poweroff"]