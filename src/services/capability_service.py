from __future__ import annotations

import shutil
from collections.abc import Callable
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

    def _make_capability(
        self,
        action_key: str,
        binary_path: str | None,
        *,
        found_template: str,
        not_found_reason: str,
    ) -> ActionCapability:
        if binary_path:
            return ActionCapability(
                action_key=action_key,
                available=True,
                reason=found_template.format(path=binary_path),
            )
        return ActionCapability(
            action_key=action_key,
            available=False,
            reason=not_found_reason,
        )

    def get_schedule_capability(self) -> ActionCapability:
        return self._make_capability(
            "schedule",
            self._probe.find_binary("systemd-run"),
            found_template="Resolved systemd-run at {path}.",
            not_found_reason="systemd-run was not found in PATH.",
        )

    def get_lock_capability(self) -> ActionCapability:
        return self._make_capability(
            "lock",
            self._probe.find_binary("loginctl"),
            found_template="Resolved loginctl at {path}.",
            not_found_reason="loginctl was not found in PATH.",
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
            if self._has_session_id():
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
                reason=(
                    "loginctl is available, but XDG_SESSION_ID is not set. "
                    "Log out requires a graphical session environment."
                ),
            )

        return ActionCapability(
            action_key="log_out",
            available=False,
            reason="Neither gnome-session-quit nor loginctl was found in PATH.",
        )

    @staticmethod
    def _has_session_id() -> bool:
        import os

        return bool(os.environ.get("XDG_SESSION_ID", "").strip())

    def get_suspend_capability(self) -> ActionCapability:
        return self._make_systemctl_kernel_capability(
            "suspend",
            self._kernel_supports_suspend,
            available_reason=(
                "Resolved systemctl at {path} and kernel sleep states "
                "indicate suspend support."
            ),
            unavailable_reason=(
                "systemctl is available, but kernel sleep states do not "
                "indicate suspend support."
            ),
        )

    def get_hibernate_capability(self) -> ActionCapability:
        return self._make_systemctl_kernel_capability(
            "hibernate",
            self._kernel_supports_hibernate,
            available_reason=(
                "Resolved systemctl at {path} and kernel power interfaces "
                "indicate hibernate support."
            ),
            unavailable_reason=(
                "systemctl is available, but kernel power interfaces do not "
                "indicate hibernate support."
            ),
        )

    def get_power_off_capability(self) -> ActionCapability:
        return self._make_capability(
            "power_off",
            self._probe.find_binary("systemctl"),
            found_template="Resolved systemctl at {path}.",
            not_found_reason="systemctl was not found in PATH.",
        )

    def _make_systemctl_kernel_capability(
        self,
        action_key: str,
        kernel_check: Callable[[], bool],
        *,
        available_reason: str,
        unavailable_reason: str,
    ) -> ActionCapability:
        systemctl = self._probe.find_binary("systemctl")
        if not systemctl:
            return self._make_capability(
                action_key,
                None,
                found_template="",
                not_found_reason="systemctl was not found in PATH.",
            )

        if kernel_check():
            return ActionCapability(
                action_key=action_key,
                available=True,
                reason=available_reason.format(path=systemctl),
            )

        return ActionCapability(
            action_key=action_key,
            available=False,
            reason=unavailable_reason,
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
