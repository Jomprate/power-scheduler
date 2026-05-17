from dataclasses import dataclass

from domain.enums import PowerAction, TimeUnit


@dataclass(slots=True)
class ScheduleRequest:
    action: PowerAction
    amount: int
    unit: TimeUnit

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Time amount must be greater than zero.")


@dataclass(slots=True)
class ScheduledJobResult:
    success: bool
    message: str
    unit_name: str | None = None
    is_user_unit: bool = False
    command: str | None = None
