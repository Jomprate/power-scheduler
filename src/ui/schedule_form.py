from __future__ import annotations

from typing import cast

from gi.repository import Gtk

from domain.enums import PowerAction, TimeUnit
from services.capability_service import ActionCapability, CapabilityService


def _build_action_list_from_caps(
    caps: dict[str, ActionCapability],
) -> list[tuple[str, PowerAction]]:
    ordered_keys = [
        ("lock", "Lock", PowerAction.LOCK),
        ("log_out", "Log out", PowerAction.LOG_OUT),
        ("suspend", "Suspend", PowerAction.SUSPEND),
        ("hibernate", "Hibernate", PowerAction.HIBERNATE),
        ("power_off", "Power off", PowerAction.POWER_OFF),
    ]
    return [
        (label, action)
        for key, label, action in ordered_keys
        if caps.get(key) and caps[key].available
    ]


class ScheduleForm(Gtk.Box):
    def __init__(self, capability_service: CapabilityService) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            margin_top=16,
            margin_bottom=16,
            margin_start=16,
            margin_end=16,
        )

        self._capability_service = capability_service
        self._action_items: list[tuple[str, PowerAction]] = []

        self.action_dropdown: Gtk.DropDown = cast(Gtk.DropDown, None)
        self.amount_spin: Gtk.SpinButton = cast(Gtk.SpinButton, None)
        self.unit_dropdown: Gtk.DropDown = cast(Gtk.DropDown, None)
        self.schedule_button: Gtk.Button = cast(Gtk.Button, None)
        self.cancel_button: Gtk.Button = cast(Gtk.Button, None)

        self._build()
        self.rebuild_action_list()

    def _build(self) -> None:
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.append(header)

        title = Gtk.Label()
        title.set_markup("<span size='13500' weight='bold'>New scheduled action</span>")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        header.append(title)

        description = Gtk.Label(label="Choose the action and the delay before it runs.")
        description.set_wrap(True)
        description.set_halign(Gtk.Align.START)
        description.set_xalign(0.0)
        description.add_css_class("dim-label")
        header.append(description)

        action_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.append(action_section)

        action_label = Gtk.Label(label="Action")
        action_label.set_halign(Gtk.Align.START)
        action_label.set_xalign(0.0)
        action_label.add_css_class("section-label")
        action_section.append(action_label)

        self.action_dropdown = Gtk.DropDown()
        self.action_dropdown.set_selected(0)
        self.action_dropdown.add_css_class("input-control")
        action_section.append(self.action_dropdown)

        time_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.append(time_section)

        time_label = Gtk.Label(label="Delay")
        time_label.set_halign(Gtk.Align.START)
        time_label.set_xalign(0.0)
        time_label.add_css_class("section-label")
        time_section.append(time_label)

        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        time_section.append(time_row)

        self.amount_spin = Gtk.SpinButton.new_with_range(1, 999999, 1)
        self.amount_spin.set_value(10)
        self.amount_spin.set_hexpand(True)
        self.amount_spin.set_width_chars(7)
        self.amount_spin.add_css_class("input-control")
        time_row.append(self.amount_spin)

        self.unit_dropdown = Gtk.DropDown.new_from_strings(
            ["Seconds", "Minutes", "Hours"]
        )
        self.unit_dropdown.set_selected(0)
        self.unit_dropdown.add_css_class("input-control")
        time_row.append(self.unit_dropdown)

        presets_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.append(presets_section)

        presets_label = Gtk.Label(label="Quick presets")
        presets_label.set_halign(Gtk.Align.START)
        presets_label.set_xalign(0.0)
        presets_label.add_css_class("section-label")
        presets_section.append(presets_label)

        presets_wrap = Gtk.FlowBox()
        presets_wrap.set_selection_mode(Gtk.SelectionMode.NONE)
        presets_wrap.set_max_children_per_line(6)
        presets_wrap.set_row_spacing(6)
        presets_wrap.set_column_spacing(6)
        presets_wrap.add_css_class("presets-wrap")
        presets_section.append(presets_wrap)

        preset_values = [
            ("10s", 10, TimeUnit.SECONDS),
            ("30s", 30, TimeUnit.SECONDS),
            ("1m", 1, TimeUnit.MINUTES),
            ("5m", 5, TimeUnit.MINUTES),
            ("15m", 15, TimeUnit.MINUTES),
            ("1h", 1, TimeUnit.HOURS),
        ]

        for label, amount, unit in preset_values:
            button = Gtk.Button(label=label)
            button.add_css_class("pill-button")
            presets_wrap.insert(button, -1)
            self._connect_preset(button, amount, unit)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.append(actions_box)

        self.schedule_button = Gtk.Button(label="Schedule")
        self.schedule_button.add_css_class("suggested-action")
        self.schedule_button.add_css_class("primary-button")
        self.schedule_button.set_hexpand(True)
        actions_box.append(self.schedule_button)

        self.cancel_button = Gtk.Button(label="Cancel scheduled action")
        self.cancel_button.add_css_class("primary-button")
        self.cancel_button.set_hexpand(True)
        self.cancel_button.set_sensitive(False)
        actions_box.append(self.cancel_button)

    def _connect_preset(self, button: Gtk.Button, amount: int, unit: TimeUnit) -> None:
        button.connect("clicked", self._on_preset_clicked, amount, unit)

    def _on_preset_clicked(
        self, _button: Gtk.Button, amount: int, unit: TimeUnit
    ) -> None:
        self.amount_spin.set_value(amount)
        self.unit_dropdown.set_selected(self.get_unit_index(unit))

    def rebuild_action_list(self) -> None:
        self._action_items = _build_action_list_from_caps(
            self._capability_service.get_capabilities()
        )
        labels = [label for label, _ in self._action_items]
        self.action_dropdown.set_model(Gtk.StringList.new(labels))

    def get_selected_action(self) -> PowerAction:
        index = self.action_dropdown.get_selected()
        if 0 <= index < len(self._action_items):
            return self._action_items[index][1]
        return self._action_items[0][1]

    def get_selected_action_label(self) -> str:
        index = self.action_dropdown.get_selected()
        if 0 <= index < len(self._action_items):
            return self._action_items[index][0]
        return self._action_items[0][0]

    def get_amount(self) -> int:
        return int(self.amount_spin.get_value())

    def get_selected_unit(self) -> TimeUnit:
        index = self.unit_dropdown.get_selected()
        mapping = {0: TimeUnit.SECONDS, 1: TimeUnit.MINUTES, 2: TimeUnit.HOURS}
        return mapping[index]

    def get_selected_unit_label(self, amount: int) -> str:
        index = self.unit_dropdown.get_selected()
        if index == 0:
            return "Second" if amount == 1 else "Seconds"
        if index == 1:
            return "Minute" if amount == 1 else "Minutes"
        return "Hour" if amount == 1 else "Hours"

    def get_action_index(self, action: PowerAction) -> int | None:
        for i, (_, act) in enumerate(self._action_items):
            if act == action:
                return i
        return None

    @staticmethod
    def get_unit_index(unit: TimeUnit) -> int:
        mapping = {
            TimeUnit.SECONDS: 0,
            TimeUnit.MINUTES: 1,
            TimeUnit.HOURS: 2,
        }
        return mapping[unit]

    def set_enabled(self, enabled: bool) -> None:
        self.schedule_button.set_sensitive(enabled)
        self.action_dropdown.set_sensitive(enabled)
        self.amount_spin.set_sensitive(enabled)
        self.unit_dropdown.set_sensitive(enabled)

    def restore(self, action: PowerAction, amount: int, unit: TimeUnit) -> None:
        idx = self.get_action_index(action)
        if idx is not None:
            self.action_dropdown.set_selected(idx)
        self.amount_spin.set_value(amount)
        self.unit_dropdown.set_selected(self.get_unit_index(unit))
