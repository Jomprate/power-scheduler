from __future__ import annotations

from domain.enums import TimeUnit


def to_seconds(amount: int, unit: TimeUnit) -> int:
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if unit == TimeUnit.SECONDS:
        return amount

    if unit == TimeUnit.MINUTES:
        return amount * 60

    if unit == TimeUnit.HOURS:
        return amount * 3600

    raise ValueError(f"Unsupported time unit: {unit}")


def format_human_time(amount: int, unit: TimeUnit) -> str:
    if unit == TimeUnit.SECONDS:
        label = "second" if amount == 1 else "seconds"
    elif unit == TimeUnit.MINUTES:
        label = "minute" if amount == 1 else "minutes"
    elif unit == TimeUnit.HOURS:
        label = "hour" if amount == 1 else "hours"
    else:
        raise ValueError("Unsupported time unit.")

    return f"{amount} {label}"
