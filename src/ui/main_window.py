from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")  # type: ignore[attr-defined]
gi.require_version("Adw", "1")  # type: ignore[attr-defined]

from gi.repository import Adw, GLib, Gtk

from app.config import APP_NAME
from domain.models import ScheduleRequest
from services.capability_service import CapabilityService
from services.schedule_controller import ScheduleController
from ui.schedule_form import ScheduleForm
from ui.status_panel import StatusPanel

DEFAULT_WIDTH = 820
DEFAULT_HEIGHT = 460


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        *,
        controller: ScheduleController,
        capability_service: CapabilityService,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.set_title(APP_NAME)
        self.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.set_resizable(True)

        self._controller = controller
        self._capability_service = capability_service
        self._form = ScheduleForm(self._capability_service)
        self._status_panel = StatusPanel()

        self._build_ui()
        self._connect_signals()
        self._restore_saved_job_if_any()
        self._refresh_summary()
        self._refresh_action_availability()

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

        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
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
        form_frame.set_child(self._form)

        content_row.append(self._status_panel)

    def _connect_signals(self) -> None:
        self._form.action_dropdown.connect("notify::selected", self._on_form_changed)
        self._form.amount_spin.connect("value-changed", self._on_form_changed)
        self._form.unit_dropdown.connect("notify::selected", self._on_form_changed)
        self._form.schedule_button.connect("clicked", self._on_schedule_clicked)
        self._form.cancel_button.connect("clicked", self._on_cancel_clicked)

    def _restore_saved_job_if_any(self) -> None:
        job = self._controller.restore_if_any()
        if job is None:
            return

        self._form.cancel_button.set_sensitive(True)

        if job.action is not None and job.unit is not None and job.amount is not None:
            self._form.restore(job.action, job.amount, job.unit)

        self._status_panel.set_status_content(
            f"Recovered scheduled action: {job.unit_name}",
            job.command,
        )

    def _on_form_changed(self, *_args) -> None:
        self._refresh_summary()
        self._refresh_action_availability()

    def _refresh_summary(self) -> None:
        action_label = self._form.get_selected_action_label()
        amount = self._form.get_amount()
        unit_label = self._form.get_selected_unit_label(amount)

        self._status_panel.set_summary(
            f"{action_label} will run in {amount} {unit_label.lower()}."
        )

    def _refresh_action_availability(self) -> None:
        self._form.schedule_button.set_sensitive(True)
        job = self._controller.active_job
        self._form.cancel_button.set_sensitive(job is not None)

    def _set_schedule_controls_enabled(self, enabled: bool) -> None:
        self._form.set_enabled(enabled)

    def _flush_ui(self) -> None:
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)

    def _on_schedule_clicked(self, _button: Gtk.Button) -> None:
        try:
            request = ScheduleRequest(
                action=self._form.get_selected_action(),
                amount=self._form.get_amount(),
                unit=self._form.get_selected_unit(),
            )

            self._status_panel.set_status_content("Scheduling action...", "")
            self._set_schedule_controls_enabled(False)
            self._flush_ui()

            result = self._controller.schedule(request)
            self._apply_schedule_result(result)
            self._notify_schedule_created(request, result)

        except Exception as exc:
            self._status_panel.set_status_content(f"Error: {exc}", "")
            self._notify_error(f"Error: {exc}")

        finally:
            self._set_schedule_controls_enabled(True)

    def _on_cancel_clicked(self, _button: Gtk.Button) -> None:
        result = self._controller.cancel()

        if result is None:
            self._status_panel.set_status_content("No scheduled action to cancel.", "")
            return

        self._status_panel.set_status_content(result.message, "")
        self._form.cancel_button.set_sensitive(False)
        self._refresh_action_availability()

        if result.success:
            self._notify_cancelled(result.message)
        else:
            self._notify_error(result.message)

    def _apply_schedule_result(self, result) -> None:
        self._status_panel.set_status_content(result.message, result.command)

        if result.unit_name:
            self._form.cancel_button.set_sensitive(True)

    def _notify_schedule_created(
        self,
        request: ScheduleRequest,
        result: object,
    ) -> None:
        app = self.get_application()
        callback = getattr(app, "show_schedule_notification", None)
        if callable(callback):
            callback(request, result)

    def _notify_cancelled(self, message: str) -> None:
        app = self.get_application()
        callback = getattr(app, "show_cancellation_notification", None)
        if callable(callback):
            callback(message)

    def _notify_error(self, message: str) -> None:
        app = self.get_application()
        callback = getattr(app, "show_error_notification", None)
        if callable(callback):
            callback(message)
