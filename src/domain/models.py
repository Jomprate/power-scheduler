from dataclasses import dataclass

from domain.enums import PowerAction, TimeUnit


@dataclass(slots=True)
class ScheduleRequest:
    action: PowerAction
    amount: int
    unit: TimeUnit