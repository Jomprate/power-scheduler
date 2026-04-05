import os


def get_current_session_id() -> str | None:
    session_id = os.environ.get("XDG_SESSION_ID")
    if session_id:
        return session_id
    return None