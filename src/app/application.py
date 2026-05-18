from __future__ import annotations

from pathlib import Path

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from app.config import APP_ID
from domain.models import ScheduledJobResult, ScheduleRequest
from services.capability_service import CapabilityService
from services.notification_service import NotificationService
from services.palette_service import PaletteService
from services.schedule_controller import ScheduleController
from ui.main_window import MainWindow


class PowerSchedulerApplication(Adw.Application):
    def __init__(
        self,
        *,
        controller: ScheduleController,
        capability_service: CapabilityService,
    ) -> None:
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

        self._controller = controller
        self.notification_service: NotificationService | None = None
        self._capability_service = capability_service
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
                controller=self._controller,
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

    def set_notification_service(
        self, notification_service: NotificationService
    ) -> None:
        self.notification_service = notification_service

    def show_schedule_notification(
        self,
        request: ScheduleRequest,
        result: ScheduledJobResult,
    ) -> None:
        if self.notification_service is not None:
            self.notification_service.send_scheduled_notification(request, result)

    def show_cancellation_notification(self, message: str) -> None:
        if self.notification_service is not None:
            self.notification_service.send_cancellation_notification(message)

    def show_error_notification(self, message: str) -> None:
        if self.notification_service is not None:
            self.notification_service.send_error_notification(message)

    def show_reminder_notification(
        self, minutes_left: int, request: ScheduleRequest
    ) -> None:
        if self.notification_service is not None:
            self.notification_service.send_reminder_notification(minutes_left, request)

    def _on_cancel_scheduled_action(
        self,
        _action: Gio.SimpleAction,
        _parameter: GLib.Variant | None,
    ) -> None:
        result = self._controller.cancel()

        if self.notification_service is None:
            return

        if result is None:
            self.notification_service.send_cancellation_notification(
                "No scheduled action was found to cancel."
            )
        elif result.success:
            self.notification_service.send_cancellation_notification(result.message)
        else:
            self.notification_service.send_error_notification(result.message)

    def _on_shutdown(self, _app: Adw.Application) -> None:
        self._palette_service.destroy()
