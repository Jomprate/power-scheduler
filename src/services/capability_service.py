from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SystemProbe(Protocol):
    def find_binary(self, name: str) -> str | None: ...
    def read_text_file(self, path: Path) -> str: ...


class HostSystemProbe:
    def find_binary(self, name: str) -> str | None:
        resolved = shutil.which(name)
        return resolved or None

    def read_text_file(self, path: Path) -> str:
        try:
            if not path.exists():
                return ""
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""


@dataclass(slots=True)
class ActionCapability:
    action_key: str
    available: bool
    reason: str


class CapabilityService:
    SYS_POWER_STATE_PATH = Path("/sys/power/state")
    SYS_POWER_DISK_PATH = Path("/sys/power/disk")

    def __init__(self, probe: SystemProbe | None = None) -> None:
        self._probe = probe or HostSystemProbe()

    def get_capabilities(self) -> dict[str, ActionCapability]:
        return {
            "lock": self.get_lock_capability(),
            "log_out": self.get_logout_capability(),
            "suspend": self.get_suspend_capability(),
            "hibernate": self.get_hibernate_capability(),
            "power_off": self.get_power_off_capability(),
            "schedule": self.get_schedule_capability(),
        }

    def get_schedule_capability(self) -> ActionCapability:
        systemd_run = self._probe.find_binary("systemd-run")

        if systemd_run:
            return ActionCapability(
                action_key="schedule",
                available=True,
                reason=f"Resolved systemd-run at {systemd_run}.",
            )

        return ActionCapability(
            action_key="schedule",
            available=False,
            reason="systemd-run was not found in PATH.",
        )

    def get_lock_capability(self) -> ActionCapability:
        loginctl = self._probe.find_binary("loginctl")

        if loginctl:
            return ActionCapability(
                action_key="lock",
                available=True,
                reason=f"Resolved loginctl at {loginctl}.",
            )

        return ActionCapability(
            action_key="lock",
            available=False,
            reason="loginctl was not found in PATH.",
        )

    def get_logout_capability(self) -> ActionCapability:
        gnome_session_quit = self._probe.find_binary("gnome-session-quit")
        if gnome_session_quit:
            return ActionCapability(
                action_key="log_out",
                available=True,
                reason=f"Resolved gnome-session-quit at {gnome_session_quit}.",
            )

        loginctl = self._probe.find_binary("loginctl")
        if loginctl:
            return ActionCapability(
                action_key="log_out",
                available=True,
                reason=(
                    "gnome-session-quit was not found, but loginctl is available "
                    f"at {loginctl} for terminate-session fallback."
                ),
            )

        return ActionCapability(
            action_key="log_out",
            available=False,
            reason="Neither gnome-session-quit nor loginctl was found in PATH.",
        )

    def get_suspend_capability(self) -> ActionCapability:
        systemctl = self._probe.find_binary("systemctl")
        if not systemctl:
            return ActionCapability(
                action_key="suspend",
                available=False,
                reason="systemctl was not found in PATH.",
            )

        if self._kernel_supports_suspend():
            return ActionCapability(
                action_key="suspend",
                available=True,
                reason=(
                    f"Resolved systemctl at {systemctl} and kernel sleep states "
                    "indicate suspend support."
                ),
            )

        return ActionCapability(
            action_key="suspend",
            available=False,
            reason=(
                "systemctl is available, but kernel sleep states do not indicate "
                "suspend support."
            ),
        )

    def get_hibernate_capability(self) -> ActionCapability:
        systemctl = self._probe.find_binary("systemctl")
        if not systemctl:
            return ActionCapability(
                action_key="hibernate",
                available=False,
                reason="systemctl was not found in PATH.",
            )

        if self._kernel_supports_hibernate():
            return ActionCapability(
                action_key="hibernate",
                available=True,
                reason=(
                    f"Resolved systemctl at {systemctl} and kernel power interfaces "
                    "indicate hibernate support."
                ),
            )

        return ActionCapability(
            action_key="hibernate",
            available=False,
            reason=(
                "systemctl is available, but kernel power interfaces do not "
                "indicate hibernate support."
            ),
        )

    def get_power_off_capability(self) -> ActionCapability:
        systemctl = self._probe.find_binary("systemctl")

        if systemctl:
            return ActionCapability(
                action_key="power_off",
                available=True,
                reason=f"Resolved systemctl at {systemctl}.",
            )

        return ActionCapability(
            action_key="power_off",
            available=False,
            reason="systemctl was not found in PATH.",
        )

    def _kernel_supports_suspend(self) -> bool:
        states = self._probe.read_text_file(self.SYS_POWER_STATE_PATH)
        if not states:
            return False

        supported_tokens = {"mem", "freeze", "standby"}
        return any(token in states.split() for token in supported_tokens)

    def _kernel_supports_hibernate(self) -> bool:
        states = self._probe.read_text_file(self.SYS_POWER_STATE_PATH)
        disk_modes = self._probe.read_text_file(self.SYS_POWER_DISK_PATH)

        if not states or not disk_modes:
            return False

        has_disk_state = "disk" in states.split()
        has_disk_mode = bool(disk_modes.strip())

        return has_disk_state and has_disk_mode
