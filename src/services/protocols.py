from __future__ import annotations

from typing import Protocol

from domain.enums import PowerAction


class PowerActionService(Protocol):
    @property
    def is_user_level(self) -> bool: ...

    def supports(self, action: PowerAction) -> bool: ...

    def build_action_command(self, action: PowerAction) -> list[str]: ...
