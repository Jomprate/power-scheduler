from __future__ import annotations

from domain.enums import TimeUnit

_UNIT_LABELS: dict[TimeUnit, tuple[str, str]] = {
    TimeUnit.SECONDS: ("second", "seconds"),
    TimeUnit.MINUTES: ("minute", "minutes"),
    TimeUnit.HOURS: ("hour", "hours"),
}


def _pluralize(singular: str, plural: str, count: int) -> str:
    return singular if count == 1 else plural


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
    try:
        singular, plural = _UNIT_LABELS[unit]
    except KeyError:
        raise ValueError("Unsupported time unit.") from None

    label = _pluralize(singular, plural, amount)
    return f"{amount} {label}"
