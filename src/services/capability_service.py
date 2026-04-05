import shutil
import subprocess


class CapabilityService:
    @staticmethod
    def has_required_commands() -> bool:
        required = ["systemd-run", "systemctl", "loginctl"]
        return all(shutil.which(cmd) is not None for cmd in required)

    @staticmethod
    def can_hibernate() -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "hibernate"],
                capture_output=True,
                text=True,
            )
            error_text = (result.stderr or "").lower()

            if "not enough swap space" in error_text:
                return False
            if "hibernation is not supported" in error_text:
                return False

            return True
        except Exception:
            return False