from domain.models import ScheduleRequest


def validate_schedule_request(request: ScheduleRequest) -> None:
    if request.amount <= 0:
        raise ValueError("Time amount must be greater than 0.")