from __future__ import annotations

import unittest

from domain.enums import PowerAction
from services.capability_service import ActionCapability
from ui.schedule_form import _build_action_list_from_caps


def _make_cap(available: bool) -> ActionCapability:
    return ActionCapability(
        action_key="",
        available=available,
        reason="",
    )


class MainWindowActionListTests(unittest.TestCase):
    def test_lists_all_actions_when_all_available(self) -> None:
        caps = {
            "lock": _make_cap(True),
            "log_out": _make_cap(True),
            "suspend": _make_cap(True),
            "hibernate": _make_cap(True),
            "power_off": _make_cap(True),
        }
        items = _build_action_list_from_caps(caps)

        expected_labels = [
            "Lock",
            "Log out",
            "Suspend",
            "Hibernate",
            "Power off",
        ]
        expected_actions = [
            PowerAction.LOCK,
            PowerAction.LOG_OUT,
            PowerAction.SUSPEND,
            PowerAction.HIBERNATE,
            PowerAction.POWER_OFF,
        ]
        self.assertEqual([label for label, _ in items], expected_labels)
        self.assertEqual([action for _, action in items], expected_actions)

    def test_omits_unavailable_actions(self) -> None:
        caps = {
            "lock": _make_cap(True),
            "log_out": _make_cap(False),
            "suspend": _make_cap(True),
            "hibernate": _make_cap(False),
            "power_off": _make_cap(True),
        }
        items = _build_action_list_from_caps(caps)
        expected = ["Lock", "Suspend", "Power off"]
        self.assertEqual([label for label, _ in items], expected)

    def test_returns_empty_when_none_available(self) -> None:
        caps = {
            key: _make_cap(False)
            for key in ["lock", "log_out", "suspend", "hibernate", "power_off"]
        }
        items = _build_action_list_from_caps(caps)
        self.assertEqual(items, [])

    def test_handles_missing_capability_keys(self) -> None:
        items = _build_action_list_from_caps({})
        self.assertEqual(items, [])

    def test_maintains_stable_order(self) -> None:
        caps = {
            "hibernate": _make_cap(True),
            "lock": _make_cap(True),
            "power_off": _make_cap(True),
        }
        items = _build_action_list_from_caps(caps)
        labels = [label for label, _ in items]
        self.assertEqual(labels, ["Lock", "Hibernate", "Power off"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
