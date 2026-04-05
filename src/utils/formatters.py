def normalize_command_output(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()