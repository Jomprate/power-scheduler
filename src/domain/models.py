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
