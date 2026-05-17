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


def to_systemd_time(amount: int, unit: TimeUnit) -> str:
    if unit == TimeUnit.SECONDS:
        return f"{amount}s"
    if unit == TimeUnit.MINUTES:
        return f"{amount}m"
    if unit == TimeUnit.HOURS:
        return f"{amount}h"
    raise ValueError("Unsupported time unit.")


def format_human_time(amount: int, unit: TimeUnit) -> str:
    if unit == TimeUnit.SECONDS:
        label = "second(s)"
    elif unit == TimeUnit.MINUTES:
        label = "minute(s)"
    elif unit == TimeUnit.HOURS:
        label = "hour(s)"
    else:
        raise ValueError("Unsupported time unit.")

    return f"{amount} {label}"