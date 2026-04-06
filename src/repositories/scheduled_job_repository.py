from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from domain.enums import PowerAction, TimeUnit


@dataclass(slots=True)
class ScheduledJobRecord:
    unit_name: str
    is_user_unit: bool
    action: PowerAction
    amount: int
    unit: TimeUnit
    command: str | None = None
    created_at: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "unit_name": self.unit_name,
            "is_user_unit": self.is_user_unit,
            "action": self.action.value,
            "amount": self.amount,
            "unit": self.unit.value,
            "command": self.command,
            "created_at": self.created_at,
        }

    @classmethod
    def from_json_dict(cls, data: Mapping[str, Any]) -> "ScheduledJobRecord":
        unit_name = cls._require_non_empty_string(data, "unit_name")
        amount = cls._require_positive_int(data, "amount")
        action = PowerAction(cls._require_non_empty_string(data, "action"))
        unit = TimeUnit(cls._require_non_empty_string(data, "unit"))
        is_user_unit = cls._require_bool(data, "is_user_unit")
        command = cls._optional_string(data, "command")
        created_at = cls._optional_string(data, "created_at")

        return cls(
            unit_name=unit_name,
            is_user_unit=is_user_unit,
            action=action,
            amount=amount,
            unit=unit,
            command=command,
            created_at=created_at,
        )

    @staticmethod
    def _require_non_empty_string(data: Mapping[str, Any], key: str) -> str:
        value = data.get(key)

        if not isinstance(value, str):
            raise ValueError(f"Stored {key} must be a string.")

        text = value.strip()
        if not text:
            raise ValueError(f"Stored {key} cannot be empty.")

        return text

    @staticmethod
    def _optional_string(data: Mapping[str, Any], key: str) -> str | None:
        value = data.get(key)

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(f"Stored {key} must be a string or null.")

        text = value.strip()
        return text or None

    @staticmethod
    def _require_bool(data: Mapping[str, Any], key: str) -> bool:
        value = data.get(key)

        if not isinstance(value, bool):
            raise ValueError(f"Stored {key} must be a boolean.")

        return value

    @staticmethod
    def _require_positive_int(data: Mapping[str, Any], key: str) -> int:
        value = data.get(key)

        if isinstance(value, bool):
            raise ValueError(f"Stored {key} must be an integer, not a boolean.")

        if not isinstance(value, int):
            raise ValueError(f"Stored {key} must be an integer.")

        if value <= 0:
            raise ValueError(f"Stored {key} must be greater than zero.")

        return value


class ScheduledJobRepository:
    """
    Persists the last scheduled system job so the app can recover it later.

    This repository intentionally stores a single current scheduled job,
    which matches the current UI model.
    """

    FILE_NAME = "current_job.json"

    def __init__(self, storage_file: Path | None = None) -> None:
        self._storage_file = storage_file or self._build_default_storage_file()

    @property
    def storage_file(self) -> Path:
        return self._storage_file

    def save_current_job(self, record: ScheduledJobRecord) -> None:
        if not record.unit_name.strip():
            raise ValueError("unit_name cannot be empty.")

        if record.amount <= 0:
            raise ValueError("amount must be greater than zero.")

        payload = record.to_json_dict()

        if not payload.get("created_at"):
            payload["created_at"] = datetime.now(timezone.utc).isoformat()

        self._storage_file.parent.mkdir(parents=True, exist_ok=True)

        temp_file = self._storage_file.with_suffix(
            self._storage_file.suffix + ".tmp"
        )
        temp_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_file.replace(self._storage_file)

    def get_current_job(self) -> ScheduledJobRecord | None:
        if not self._storage_file.exists():
            return None

        try:
            raw_text = self._storage_file.read_text(encoding="utf-8").strip()
            if not raw_text:
                return None

            payload = json.loads(raw_text)

            if not isinstance(payload, dict):
                return None

            return ScheduledJobRecord.from_json_dict(payload)
        except Exception:
            return None

    def clear_current_job(self) -> None:
        try:
            if self._storage_file.exists():
                self._storage_file.unlink()
        except FileNotFoundError:
            pass

    def has_current_job(self) -> bool:
        return self.get_current_job() is not None

    @staticmethod
    def _build_default_storage_file() -> Path:
        state_home = os.environ.get("XDG_STATE_HOME", "").strip()

        if state_home:
            base_dir = Path(state_home)
        else:
            base_dir = Path.home() / ".local" / "state"

        return base_dir / "power-scheduler" / ScheduledJobRepository.FILE_NAME