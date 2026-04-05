from enum import Enum


class PowerAction(str, Enum):
    LOCK = "lock"
    LOG_OUT = "log_out"
    SUSPEND = "suspend"
    HIBERNATE = "hibernate"
    POWER_OFF = "power_off"


class TimeUnit(str, Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"