from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil


@dataclass(slots=True)
class ActionCapability:
    action_key: str
    available: bool
    reason: str


class CapabilityService:
    """
    Detects whether each supported action is likely available on the host.

    Design goals:
    - do not execute destructive power actions just to "test" them
    - expose capability per action instead of a single global boolean
    - keep the checks lightweight and safe for app startup / UI refresh
    """

    SYS_POWER_STATE_PATH = Path("/sys/power/state")
    SYS_POWER_DISK_PATH = Path("/sys/power/disk")

    @classmethod
    def has_required_commands(cls) -> bool:
        """
        Backward-compatible coarse check.

        This answers whether the core command set used by the app exists,
        but it should not be used as the only source of truth for UI state.
        """
        required = ["systemd-run", "systemctl", "loginctl"]
        return all(cls._which(cmd) is not None for cmd in required)

    @classmethod
    def get_capabilities(cls) -> dict[str, ActionCapability]:
        return {
            "lock": cls.get_lock_capability(),
            "log_out": cls.get_logout_capability(),
            "suspend": cls.get_suspend_capability(),
            "hibernate": cls.get_hibernate_capability(),
            "power_off": cls.get_power_off_capability(),
            "schedule": cls.get_schedule_capability(),
        }

    @classmethod
    def get_schedule_capability(cls) -> ActionCapability:
        systemd_run = cls._which("systemd-run")

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

    @classmethod
    def get_lock_capability(cls) -> ActionCapability:
        loginctl = cls._which("loginctl")

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

    @classmethod
    def get_logout_capability(cls) -> ActionCapability:
        gnome_session_quit = cls._which("gnome-session-quit")
        if gnome_session_quit:
            return ActionCapability(
                action_key="log_out",
                available=True,
                reason=f"Resolved gnome-session-quit at {gnome_session_quit}.",
            )

        loginctl = cls._which("loginctl")
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

    @classmethod
    def get_suspend_capability(cls) -> ActionCapability:
        systemctl = cls._which("systemctl")
        if not systemctl:
            return ActionCapability(
                action_key="suspend",
                available=False,
                reason="systemctl was not found in PATH.",
            )

        if cls._kernel_supports_suspend():
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

    @classmethod
    def get_hibernate_capability(cls) -> ActionCapability:
        systemctl = cls._which("systemctl")
        if not systemctl:
            return ActionCapability(
                action_key="hibernate",
                available=False,
                reason="systemctl was not found in PATH.",
            )

        if cls._kernel_supports_hibernate():
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

    @classmethod
    def get_power_off_capability(cls) -> ActionCapability:
        systemctl = cls._which("systemctl")

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

    @classmethod
    def can_hibernate(cls) -> bool:
        """
        Backward-compatible boolean helper.
        """
        return cls.get_hibernate_capability().available

    @classmethod
    def can_suspend(cls) -> bool:
        return cls.get_suspend_capability().available

    @classmethod
    def can_lock(cls) -> bool:
        return cls.get_lock_capability().available

    @classmethod
    def can_logout(cls) -> bool:
        return cls.get_logout_capability().available

    @classmethod
    def can_power_off(cls) -> bool:
        return cls.get_power_off_capability().available

    @classmethod
    def _kernel_supports_suspend(cls) -> bool:
        states = cls._read_text_if_exists(cls.SYS_POWER_STATE_PATH)
        if not states:
            return False

        supported_tokens = {"mem", "freeze", "standby"}
        return any(token in states.split() for token in supported_tokens)

    @classmethod
    def _kernel_supports_hibernate(cls) -> bool:
        states = cls._read_text_if_exists(cls.SYS_POWER_STATE_PATH)
        disk_modes = cls._read_text_if_exists(cls.SYS_POWER_DISK_PATH)

        if not states or not disk_modes:
            return False

        has_disk_state = "disk" in states.split()
        has_disk_mode = bool(disk_modes.strip())

        return has_disk_state and has_disk_mode

    @staticmethod
    def _read_text_if_exists(path: Path) -> str:
        try:
            if not path.exists():
                return ""
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    @staticmethod
    def _which(binary_name: str) -> str | None:
        resolved = shutil.which(binary_name)
        return resolved or None