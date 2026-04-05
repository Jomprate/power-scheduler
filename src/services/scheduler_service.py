from dataclasses import dataclass
from datetime import datetime

from domain.enums import PowerAction
from domain.models import ScheduleRequest
from domain.validators import validate_schedule_request
from services.command_builder import CommandBuilder
from utils.process_utils import run_command
from utils.time_utils import format_human_time


@dataclass(slots=True)
class ScheduledJobResult:
    success: bool
    message: str
    unit_name: str | None = None
    is_user_unit: bool = False
    command: str | None = None


class SchedulerService:
    USER_ACTIONS = {
        PowerAction.LOCK,
        PowerAction.LOG_OUT,
    }

    def schedule(self, request: ScheduleRequest) -> ScheduledJobResult:
        validate_schedule_request(request)

        unit_name = self._generate_unit_name(request.action)
        is_user_unit = request.action in self.USER_ACTIONS

        command = CommandBuilder.build_schedule_command(
            request=request,
            unit_name=unit_name,
        )
        result = run_command(command)

        scheduled_for = format_human_time(request.amount, request.unit)
        stdout = (result.stdout or "").strip()
        base_message = (
            f"Scheduled {request.action.value} in {scheduled_for}. "
            f"Unit: {unit_name}"
        )

        if stdout:
            base_message = f"{base_message}\n{stdout}"

        return ScheduledJobResult(
            success=True,
            message=base_message,
            unit_name=unit_name,
            is_user_unit=is_user_unit,
            command=" ".join(command),
        )

    def cancel(self, unit_name: str, is_user_unit: bool) -> ScheduledJobResult:
        base_command = ["systemctl"]
        if is_user_unit:
            base_command.append("--user")

        run_command([*base_command, "stop", f"{unit_name}.timer"], check=False)
        run_command([*base_command, "stop", f"{unit_name}.service"], check=False)
        run_command([*base_command, "reset-failed"], check=False)

        return ScheduledJobResult(
            success=True,
            message=f"Cancelled scheduled action for unit: {unit_name}",
            unit_name=unit_name,
            is_user_unit=is_user_unit,
            command=None,
        )

    def _generate_unit_name(self, action: PowerAction) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"power-scheduler-{action.value}-{timestamp}"