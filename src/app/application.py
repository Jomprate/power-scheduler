import gi

gi.require_version("Gtk", "4.0")  # type: ignore
gi.require_version("Adw", "1")  # type: ignore

from pathlib import Path

from gi.repository import Adw, Gdk, Gio, Gtk, GLib

from app.config import APP_ID
from domain.models import ScheduleRequest
from repositories.scheduled_job_repository import ScheduledJobRepository
from services.notification_service import NotificationService
from services.scheduler_service import ScheduledJobResult, SchedulerService
from ui.main_window import MainWindow


class PowerSchedulerApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

        self._app_css_provider: Gtk.CssProvider | None = None
        self._app_css_loaded = False

        self._system_palette_provider: Gtk.CssProvider | None = None

        self._style_manager = Adw.StyleManager.get_default()
        self._style_manager_handler_id: int | None = None

        self._file_monitors: list[Gio.FileMonitor] = []
        self._monitors_started = False
        self._reload_timeout_id: int | None = None

        self.scheduled_job_repository = ScheduledJobRepository()
        self.scheduler_service = SchedulerService(
            scheduled_job_repository=self.scheduled_job_repository
        )
        self.notification_service = NotificationService(self)

        self._register_actions()

    def _register_actions(self) -> None:
        cancel_action = Gio.SimpleAction.new("cancel-scheduled", None)
        cancel_action.connect("activate", self._on_cancel_scheduled_action)
        self.add_action(cancel_action)

    def _on_activate(self, _app) -> None:
        self._ensure_css_loaded()
        self._ensure_system_palette_loaded()
        self._ensure_theme_binding()
        self._ensure_palette_monitors()

        window = self.props.active_window
        if window is None:
            window = MainWindow(
                application=self,
                scheduler_service=self.scheduler_service,
            )

        window.present()

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
                self.notification_service.send_cancellation_notification(
                    result.message
                )
            else:
                self.notification_service.send_error_notification(result.message)

        except Exception as exc:
            self.notification_service.send_error_notification(f"Error: {exc}")

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

        self._app_css_provider = css_provider
        self._app_css_loaded = True

    def _ensure_system_palette_loaded(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return

        if self._system_palette_provider is None:
            self._system_palette_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                display,
                self._system_palette_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
            )

        self._reload_system_palette()

    def _ensure_theme_binding(self) -> None:
        if self._style_manager_handler_id is not None:
            return

        self._style_manager_handler_id = self._style_manager.connect(
            "notify::dark",
            self._on_dark_changed,
        )

    def _ensure_palette_monitors(self) -> None:
        if self._monitors_started:
            return

        self._monitors_started = True

        paths_to_watch = [
            Path.home() / ".config" / "gtk-4.0" / "gtk.css",
            Path.home() / ".config" / "gtk-4.0" / "cosmic" / "light.css",
            Path.home() / ".config" / "gtk-4.0" / "cosmic" / "dark.css",
        ]

        for path in paths_to_watch:
            self._try_watch_file(path)

    def _try_watch_file(self, path: Path) -> None:
        try:
            gio_file = Gio.File.new_for_path(str(path))
            monitor = gio_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", self._on_palette_file_changed)
            self._file_monitors.append(monitor)
        except Exception:
            pass

    def _on_dark_changed(self, *_args) -> None:
        self._schedule_palette_reload()

    def _on_palette_file_changed(
        self,
        _monitor: Gio.FileMonitor,
        _file: Gio.File,
        _other_file: Gio.File | None,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        relevant_events = {
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.DELETED,
            Gio.FileMonitorEvent.MOVED,
            Gio.FileMonitorEvent.MOVED_IN,
            Gio.FileMonitorEvent.MOVED_OUT,
            Gio.FileMonitorEvent.RENAMED,
            Gio.FileMonitorEvent.ATTRIBUTE_CHANGED,
        }

        if event_type in relevant_events:
            self._schedule_palette_reload()

    def _schedule_palette_reload(self) -> None:
        if self._reload_timeout_id is not None:
            GLib.source_remove(self._reload_timeout_id)

        self._reload_timeout_id = GLib.timeout_add(
            120,
            self._debounced_reload_system_palette,
        )

    def _debounced_reload_system_palette(self) -> bool:
        self._reload_timeout_id = None
        self._reload_system_palette()
        return False

    def _reload_system_palette(self) -> None:
        if self._system_palette_provider is None:
            return

        css_data = self._build_system_palette_css()
        if not css_data.strip():
            return

        if hasattr(self._system_palette_provider, "load_from_string"):
            self._system_palette_provider.load_from_string(css_data)
        else:
            self._system_palette_provider.load_from_data(css_data.encode("utf-8"))

        self._invalidate_all_windows()

    def _invalidate_all_windows(self) -> None:
        for window in self.get_windows():
            try:
                window.queue_draw()
            except Exception:
                pass

    def _build_system_palette_css(self) -> str:
        palette_file = self._get_preferred_palette_file()
        if palette_file is None or not palette_file.exists():
            fallback = self._get_user_gtk_css_file()
            if fallback is None or not fallback.exists():
                return ""
            palette_file = fallback

        raw_text = self._read_text_safe(palette_file)
        if not raw_text:
            return ""

        define_lines: list[str] = []
        for line in raw_text.splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("/*") or stripped.startswith("//"):
                continue

            if stripped.startswith("@define-color "):
                define_lines.append(stripped)

        if not define_lines:
            return ""

        return "/* Imported COSMIC system palette */\n" + "\n".join(define_lines) + "\n"

    def _get_preferred_palette_file(self) -> Path | None:
        cosmic_dir = Path.home() / ".config" / "gtk-4.0" / "cosmic"

        if self._style_manager.get_dark():
            preferred = cosmic_dir / "dark.css"
        else:
            preferred = cosmic_dir / "light.css"

        if preferred.exists():
            return preferred

        return None

    def _get_user_gtk_css_file(self) -> Path | None:
        path = Path.home() / ".config" / "gtk-4.0" / "gtk.css"
        if path.exists():
            return path
        return None

    @staticmethod
    def _read_text_safe(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return ""
        except Exception:
            return ""