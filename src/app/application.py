from __future__ import annotations

from pathlib import Path

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from app.config import APP_ID
from domain.models import ScheduleRequest
from services.capability_service import CapabilityService
from services.notification_service import NotificationService
from services.palette_service import PaletteService
from services.scheduler_service import ScheduledJobResult, SchedulerService
from ui.main_window import MainWindow


class PowerSchedulerApplication(Adw.Application):
    def __init__(
        self,
        *,
        scheduler_service: SchedulerService | None = None,
        notification_service: NotificationService | None = None,
        capability_service: CapabilityService | None = None,
    ) -> None:
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

        self.scheduler_service = scheduler_service or SchedulerService()
        self.notification_service = notification_service or NotificationService(self)
        self._capability_service = capability_service or CapabilityService()
        self._palette_service = PaletteService(self)
        self._app_css_loaded = False

        self._register_actions()

    def _register_actions(self) -> None:
        cancel_action = Gio.SimpleAction.new("cancel-scheduled", None)
        cancel_action.connect("activate", self._on_cancel_scheduled_action)
        self.add_action(cancel_action)

    def _on_activate(self, _app) -> None:
        self._ensure_css_loaded()
        self._palette_service.ensure_loaded()

        window = self.props.active_window
        if window is None:
            window = MainWindow(
                application=self,
                scheduler_service=self.scheduler_service,
                capability_service=self._capability_service,
            )

        window.present()

    def _ensure_css_loaded(self) -> None:
        if self._app_css_loaded:
            return

        css_path = (
            Path(__file__).resolve().parent.parent.parent
            / "assets"
            / "styles"
            / "app.css"
        )

        if not css_path.exists():
            return

        display = Gdk.Display.get_default()
        if display is None:
            return

        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(str(css_path))

        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self._app_css_loaded = True

    def show_schedule_notification(
        self,
        request: ScheduleRequest,
        result: ScheduledJobResult,
    ) -> None:
        self.notification_service.send_scheduled_notification(request, result)

    def show_cancellation_notification(self, message: str) -> None:
        self.notification_service.send_cancellation_notification(message)

    def show_error_notification(self, message: str) -> None:
        self.notification_service.send_error_notification(message)

    def _on_cancel_scheduled_action(
        self,
        _action: Gio.SimpleAction,
        _parameter: GLib.Variant | None,
    ) -> None:
        stored_job = self.scheduler_service.get_current_scheduled_job()

        if stored_job is None:
            self.notification_service.send_cancellation_notification(
                "No scheduled action was found to cancel."
            )
            return

        try:
            result = self.scheduler_service.cancel(
                stored_job.unit_name,
                stored_job.is_user_unit,
            )

            if result.success:
                self.notification_service.send_cancellation_notification(result.message)
            else:
                self.notification_service.send_error_notification(result.message)

        except Exception as exc:
            self.notification_service.send_error_notification(f"Error: {exc}")
