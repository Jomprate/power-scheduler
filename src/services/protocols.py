from __future__ import annotations

from typing import Protocol

from domain.enums import PowerAction


class PowerActionService(Protocol):
    def supports(self, action: PowerAction) -> bool: ...

    def build_action_command(self, action: PowerAction) -> list[str]: ...
