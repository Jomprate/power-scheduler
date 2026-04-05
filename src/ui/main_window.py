from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")  # type: ignore
gi.require_version("Adw", "1")  # type: ignore

from typing import cast

from gi.repository import Adw, GLib, Gtk

from app.config import APP_NAME
from domain.enums import PowerAction, TimeUnit
from domain.models import ScheduleRequest
from services.scheduler_service import SchedulerService, ScheduledJobResult


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.set_title(APP_NAME)
        self.set_default_size(820, 460)
        self.set_resizable(True)

        self.scheduler_service = SchedulerService()
        self.current_unit_name: str | None = None
        self.current_is_user_unit: bool = False
        self.current_command: str | None = None

        self.action_dropdown: Gtk.DropDown = cast(Gtk.DropDown, None)
        self.amount_spin: Gtk.SpinButton = cast(Gtk.SpinButton, None)
        self.unit_dropdown: Gtk.DropDown = cast(Gtk.DropDown, None)
        self.status_label: Gtk.Label = cast(Gtk.Label, None)
        self.command_label: Gtk.Label = cast(Gtk.Label, None)
        self.summary_label: Gtk.Label = cast(Gtk.Label, None)
        self.schedule_button: Gtk.Button = cast(Gtk.Button, None)
        self.cancel_button: Gtk.Button = cast(Gtk.Button, None)

        self._build_ui()
        self._refresh_summary()

    def _build_ui(self) -> None:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_css_class("background")
        toolbar_view.add_css_class("app-shell")
        self.set_content(toolbar_view)

        header_bar = Adw.HeaderBar()
        header_bar.set_show_start_title_buttons(False)
        header_bar.set_show_end_title_buttons(True)
        header_bar.set_decoration_layout(":minimize,maximize,close")
        header_bar.add_css_class("app-headerbar")
        header_bar.set_title_widget(
            Adw.WindowTitle(
                title="Power Scheduler",
                subtitle="Schedule Linux power actions",
            )
        )
        toolbar_view.add_top_bar(header_bar)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(980)
        toolbar_view.set_content(clamp)

        page_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            margin_top=18,
            margin_bottom=18,
            margin_start=18,
            margin_end=18,
        )
        page_box.set_valign(Gtk.Align.START)
        page_box.add_css_class("background")
        page_box.add_css_class("page-root")
        page_box.add_css_class("content-surface")
        clamp.set_child(page_box)

        hero_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )
        hero_box.add_css_class("hero-box")
        page_box.append(hero_box)

        eyebrow = Gtk.Label(label="Power Management")
        eyebrow.set_halign(Gtk.Align.START)
        eyebrow.set_xalign(0.0)
        eyebrow.add_css_class("eyebrow")
        hero_box.append(eyebrow)

        page_title = Gtk.Label()
        page_title.set_markup(
            "<span size='17000' weight='bold'>Schedule actions for your system</span>"
        )
        page_title.set_halign(Gtk.Align.START)
        page_title.set_xalign(0.0)
        hero_box.append(page_title)

        page_subtitle = Gtk.Label(
            label=(
                "Create a delayed lock, log out, suspend, hibernate or power off "
                "without keeping the app open."
            )
        )
        page_subtitle.set_wrap(True)
        page_subtitle.set_halign(Gtk.Align.START)
        page_subtitle.set_xalign(0.0)
        page_subtitle.add_css_class("dim-label")
        hero_box.append(page_subtitle)

        content_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )
        content_row.set_hexpand(True)
        content_row.set_valign(Gtk.Align.START)
        page_box.append(content_row)

        form_frame = Gtk.Frame()
        form_frame.set_hexpand(True)
        form_frame.set_valign(Gtk.Align.START)
        form_frame.add_css_class("card")
        form_frame.add_css_class("main-card")
        content_row.append(form_frame)

        form_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            margin_top=16,
            margin_bottom=16,
            margin_start=16,
            margin_end=16,
        )
        form_frame.set_child(form_box)

        form_header = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )
        form_box.append(form_header)

        form_title = Gtk.Label()
        form_title.set_markup(
            "<span size='13500' weight='bold'>New scheduled action</span>"
        )
        form_title.set_halign(Gtk.Align.START)
        form_title.set_xalign(0.0)
        form_header.append(form_title)

        form_description = Gtk.Label(
            label="Choose the action and the delay before it runs."
        )
        form_description.set_wrap(True)
        form_description.set_halign(Gtk.Align.START)
        form_description.set_xalign(0.0)
        form_description.add_css_class("dim-label")
        form_header.append(form_description)

        action_section = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5,
        )
        form_box.append(action_section)

        action_label = Gtk.Label(label="Action")
        action_label.set_halign(Gtk.Align.START)
        action_label.set_xalign(0.0)
        action_label.add_css_class("section-label")
        action_section.append(action_label)

        action_dropdown = Gtk.DropDown.new_from_strings(
            [
                "Lock",
                "Log out",
                "Suspend",
                "Hibernate",
                "Power off",
            ]
        )
        action_dropdown.set_selected(0)
        action_dropdown.add_css_class("input-control")
        action_dropdown.connect("notify::selected", self._on_form_changed)
        action_section.append(action_dropdown)
        self.action_dropdown = action_dropdown

        time_section = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5,
        )
        form_box.append(time_section)

        time_label = Gtk.Label(label="Delay")
        time_label.set_halign(Gtk.Align.START)
        time_label.set_xalign(0.0)
        time_label.add_css_class("section-label")
        time_section.append(time_label)

        time_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        time_section.append(time_row)

        amount_spin = Gtk.SpinButton.new_with_range(1, 999999, 1)
        amount_spin.set_value(10)
        amount_spin.set_hexpand(True)
        amount_spin.set_width_chars(7)
        amount_spin.add_css_class("input-control")
        amount_spin.connect("value-changed", self._on_form_changed)
        time_row.append(amount_spin)
        self.amount_spin = amount_spin

        unit_dropdown = Gtk.DropDown.new_from_strings(
            [
                "Seconds",
                "Minutes",
                "Hours",
            ]
        )
        unit_dropdown.set_selected(0)
        unit_dropdown.add_css_class("input-control")
        unit_dropdown.connect("notify::selected", self._on_form_changed)
        time_row.append(unit_dropdown)
        self.unit_dropdown = unit_dropdown

        presets_section = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
        )
        form_box.append(presets_section)

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
            button.connect("clicked", self._on_preset_clicked, amount, unit)
            presets_wrap.insert(button, -1)

        actions_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        form_box.append(actions_box)

        schedule_button = Gtk.Button(label="Schedule")
        schedule_button.add_css_class("suggested-action")
        schedule_button.add_css_class("primary-button")
        schedule_button.set_hexpand(True)
        schedule_button.connect("clicked", self._on_schedule_clicked)
        actions_box.append(schedule_button)
        self.schedule_button = schedule_button

        cancel_button = Gtk.Button(label="Cancel scheduled action")
        cancel_button.add_css_class("primary-button")
        cancel_button.set_hexpand(True)
        cancel_button.set_sensitive(False)
        cancel_button.connect("clicked", self._on_cancel_clicked)
        actions_box.append(cancel_button)
        self.cancel_button = cancel_button

        side_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        side_box.set_size_request(280, -1)
        side_box.set_valign(Gtk.Align.START)
        content_row.append(side_box)

        summary_frame = Gtk.Frame()
        summary_frame.add_css_class("card")
        summary_frame.add_css_class("status-card")
        side_box.append(summary_frame)

        summary_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        summary_frame.set_child(summary_box)

        summary_title = Gtk.Label()
        summary_title.set_markup("<span weight='bold'>Summary</span>")
        summary_title.set_halign(Gtk.Align.START)
        summary_title.set_xalign(0.0)
        summary_box.append(summary_title)

        self.summary_label = Gtk.Label(label="")
        self.summary_label.set_wrap(True)
        self.summary_label.set_halign(Gtk.Align.START)
        self.summary_label.set_xalign(0.0)
        summary_box.append(self.summary_label)

        status_frame = Gtk.Frame()
        status_frame.add_css_class("card")
        status_frame.add_css_class("status-card")
        side_box.append(status_frame)

        status_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        status_frame.set_child(status_box)

        status_title = Gtk.Label()
        status_title.set_markup("<span weight='bold'>Status</span>")
        status_title.set_halign(Gtk.Align.START)
        status_title.set_xalign(0.0)
        status_box.append(status_title)

        self.status_label = Gtk.Label(
            label="Choose an action and a delay, then schedule it."
        )
        self.status_label.set_wrap(True)
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_xalign(0.0)
        status_box.append(self.status_label)

        self.command_label = Gtk.Label(label="")
        self.command_label.set_wrap(True)
        self.command_label.set_halign(Gtk.Align.START)
        self.command_label.set_xalign(0.0)
        self.command_label.set_selectable(True)
        self.command_label.add_css_class("dim-label")
        status_box.append(self.command_label)

        hints_frame = Gtk.Frame()
        hints_frame.add_css_class("card")
        hints_frame.add_css_class("status-card")
        side_box.append(hints_frame)

        hints_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        hints_frame.set_child(hints_box)

        hints_title = Gtk.Label()
        hints_title.set_markup("<span weight='bold'>Notes</span>")
        hints_title.set_halign(Gtk.Align.START)
        hints_title.set_xalign(0.0)
        hints_box.append(hints_title)

        hints_text = Gtk.Label(
            label=(
                "Scheduled actions are created through system tools so they can "
                "continue after this window is closed."
            )
        )
        hints_text.set_wrap(True)
        hints_text.set_halign(Gtk.Align.START)
        hints_text.set_xalign(0.0)
        hints_text.add_css_class("dim-label")
        hints_box.append(hints_text)

    def _on_form_changed(self, *_args) -> None:
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        action_label = self._get_selected_action_label()
        amount = int(self.amount_spin.get_value())
        unit_label = self._get_selected_unit_label(amount)

        self.summary_label.set_text(
            f"{action_label} will run in {amount} {unit_label.lower()}."
        )

    def _on_preset_clicked(
        self,
        _button: Gtk.Button,
        amount: int,
        unit: TimeUnit,
    ) -> None:
        self.amount_spin.set_value(amount)

        unit_mapping = {
            TimeUnit.SECONDS: 0,
            TimeUnit.MINUTES: 1,
            TimeUnit.HOURS: 2,
        }

        self.unit_dropdown.set_selected(unit_mapping[unit])
        self._refresh_summary()

    def _set_schedule_controls_enabled(self, enabled: bool) -> None:
        self.schedule_button.set_sensitive(enabled)
        self.action_dropdown.set_sensitive(enabled)
        self.amount_spin.set_sensitive(enabled)
        self.unit_dropdown.set_sensitive(enabled)

    def _flush_ui(self) -> None:
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)

    def _on_schedule_clicked(self, _button: Gtk.Button) -> None:
        try:
            request = ScheduleRequest(
                action=self._get_selected_action(),
                amount=int(self.amount_spin.get_value()),
                unit=self._get_selected_unit(),
            )

            self.status_label.set_text("Scheduling action...")
            self.command_label.set_text("")
            self._set_schedule_controls_enabled(False)
            self._flush_ui()

            result = self.scheduler_service.schedule(request)
            self._apply_schedule_result(result)

        except Exception as exc:
            self.status_label.set_text(f"Error: {exc}")
            self.command_label.set_text("")

        finally:
            self._set_schedule_controls_enabled(True)

    def _on_cancel_clicked(self, _button: Gtk.Button) -> None:
        if not self.current_unit_name:
            self.status_label.set_text("No scheduled action to cancel.")
            self.command_label.set_text("")
            return

        try:
            result = self.scheduler_service.cancel(
                self.current_unit_name,
                self.current_is_user_unit,
            )
            self.status_label.set_text(result.message)
            self.command_label.set_text("")
            self.current_unit_name = None
            self.current_is_user_unit = False
            self.current_command = None
            self.cancel_button.set_sensitive(False)
        except Exception as exc:
            self.status_label.set_text(f"Error: {exc}")

    def _apply_schedule_result(self, result: ScheduledJobResult) -> None:
        self.status_label.set_text(result.message)

        if result.command:
            self.command_label.set_text(result.command)
        else:
            self.command_label.set_text("")

        if result.unit_name:
            self.current_unit_name = result.unit_name
            self.current_is_user_unit = result.is_user_unit
            self.current_command = result.command
            self.cancel_button.set_sensitive(True)

    def _get_selected_action(self) -> PowerAction:
        index = self.action_dropdown.get_selected()

        mapping = {
            0: PowerAction.LOCK,
            1: PowerAction.LOG_OUT,
            2: PowerAction.SUSPEND,
            3: PowerAction.HIBERNATE,
            4: PowerAction.POWER_OFF,
        }

        return mapping[index]

    def _get_selected_action_label(self) -> str:
        mapping = {
            0: "Lock",
            1: "Log out",
            2: "Suspend",
            3: "Hibernate",
            4: "Power off",
        }

        return mapping[self.action_dropdown.get_selected()]

    def _get_selected_unit(self) -> TimeUnit:
        index = self.unit_dropdown.get_selected()

        mapping = {
            0: TimeUnit.SECONDS,
            1: TimeUnit.MINUTES,
            2: TimeUnit.HOURS,
        }

        return mapping[index]

    def _get_selected_unit_label(self, amount: int) -> str:
        index = self.unit_dropdown.get_selected()

        if index == 0:
            return "Second" if amount == 1 else "Seconds"

        if index == 1:
            return "Minute" if amount == 1 else "Minutes"

        return "Hour" if amount == 1 else "Hours"