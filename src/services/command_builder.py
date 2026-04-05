from domain.enums import PowerAction
from domain.models import ScheduleRequest
from utils.linux_utils import get_current_session_id
from utils.time_utils import to_systemd_time


class CommandBuilder:
    @staticmethod
    def build_schedule_command(
        request: ScheduleRequest,
        unit_name: str,
    ) -> list[str]:
        delay = to_systemd_time(request.amount, request.unit)

        if request.action == PowerAction.LOCK:
            session_id = get_current_session_id()
            if not session_id:
                raise RuntimeError(
                    "Could not determine current session ID for lock action."
                )

            return [
                "systemd-run",
                "--user",
                "--on-active",
                delay,
                "--unit",
                unit_name,
                "loginctl",
                "lock-session",
                session_id,
            ]

        if request.action == PowerAction.LOG_OUT:
            session_id = get_current_session_id()
            if not session_id:
                raise RuntimeError(
                    "Could not determine current session ID for log out."
                )

            return [
                "systemd-run",
                "--user",
                "--on-active",
                delay,
                "--unit",
                unit_name,
                "loginctl",
                "terminate-session",
                session_id,
            ]

        if request.action == PowerAction.SUSPEND:
            return [
                "systemd-run",
                "--on-active",
                delay,
                "--unit",
                unit_name,
                "systemctl",
                "suspend",
            ]

        if request.action == PowerAction.HIBERNATE:
            return [
                "systemd-run",
                "--on-active",
                delay,
                "--unit",
                unit_name,
                "systemctl",
                "hibernate",
            ]

        if request.action == PowerAction.POWER_OFF:
            return [
                "systemd-run",
                "--on-active",
                delay,
                "--unit",
                unit_name,
                "systemctl",
                "poweroff",
            ]

        raise ValueError("Unsupported action.")