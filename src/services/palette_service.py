from __future__ import annotations

from pathlib import Path

from gi.repository import Adw, Gdk, Gio, GLib, Gtk


class PaletteService:
    def __init__(self, app: Adw.Application) -> None:
        self._app = app
        self._provider: Gtk.CssProvider | None = None
        self._style_manager = Adw.StyleManager.get_default()
        self._style_manager_handler_id: int | None = None
        self._file_monitors: list[Gio.FileMonitor] = []
        self._monitors_started = False
        self._reload_timeout_id: int | None = None

    def ensure_loaded(self) -> None:
        self._ensure_provider()
        self._ensure_theme_binding()
        self._ensure_monitors()
        self._reload()

    def _ensure_provider(self) -> None:
        if self._provider is not None:
            return

        display = Gdk.Display.get_default()
        if display is None:
            return

        self._provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display,
            self._provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )

    def _ensure_theme_binding(self) -> None:
        if self._style_manager_handler_id is not None:
            return

        self._style_manager_handler_id = self._style_manager.connect(
            "notify::dark",
            self._on_dark_changed,
        )

    def _ensure_monitors(self) -> None:
        if self._monitors_started:
            return

        self._monitors_started = True

        paths = [
            Path.home() / ".config" / "gtk-4.0" / "gtk.css",
            Path.home() / ".config" / "gtk-4.0" / "cosmic" / "light.css",
            Path.home() / ".config" / "gtk-4.0" / "cosmic" / "dark.css",
        ]

        for path in paths:
            self._try_watch(path)

    def _try_watch(self, path: Path) -> None:
        try:
            gio_file = Gio.File.new_for_path(str(path))
            monitor = gio_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", self._on_file_changed)
            self._file_monitors.append(monitor)
        except Exception:
            pass

    def _on_dark_changed(self, *_args) -> None:
        self._schedule_reload()

    def _on_file_changed(
        self,
        _monitor: Gio.FileMonitor,
        _file: Gio.File,
        _other_file: Gio.File | None,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        relevant = {
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

        if event_type in relevant:
            self._schedule_reload()

    def _schedule_reload(self) -> None:
        if self._reload_timeout_id is not None:
            GLib.source_remove(self._reload_timeout_id)

        self._reload_timeout_id = GLib.timeout_add(120, self._debounced_reload)

    def _debounced_reload(self) -> bool:
        self._reload_timeout_id = None
        self._reload()
        return False

    def _reload(self) -> None:
        if self._provider is None:
            return

        css = self._build_palette_css()
        if not css.strip():
            self._provider.load_from_string("")
        else:
            if hasattr(self._provider, "load_from_string"):
                self._provider.load_from_string(css)
            else:
                self._provider.load_from_data(css.encode("utf-8"))

        self._invalidate_windows()

    def _invalidate_windows(self) -> None:
        for window in self._app.get_windows():
            try:
                window.queue_draw()
                window.queue_resize()
            except Exception:
                pass

    def _build_palette_css(self) -> str:
        palette_file = self._get_preferred_palette()
        if palette_file is None or not palette_file.exists():
            fallback = self._get_user_css()
            if fallback is None or not fallback.exists():
                return ""
            palette_file = fallback

        raw = self._read_safe(palette_file)
        if not raw:
            return ""

        define_lines: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("/*") or stripped.startswith("//"):
                continue
            if stripped.startswith("@define-color "):
                define_lines.append(stripped)

        if not define_lines:
            return ""

        return "/* Imported system palette */\n" + "\n".join(define_lines) + "\n"

    def _get_preferred_palette(self) -> Path | None:
        cosmic_dir = Path.home() / ".config" / "gtk-4.0" / "cosmic"

        if self._style_manager.get_dark():
            preferred = cosmic_dir / "dark.css"
        else:
            preferred = cosmic_dir / "light.css"

        return preferred if preferred.exists() else None

    def _get_user_css(self) -> Path | None:
        path = Path.home() / ".config" / "gtk-4.0" / "gtk.css"
        return path if path.exists() else None

    @staticmethod
    def _read_safe(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return ""
        except Exception:
            return ""
