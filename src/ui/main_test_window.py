import sys
import gi

gi.require_version("Gtk", "4.0")  # type: ignore
gi.require_version("Adw", "1")  # type: ignore

from gi.repository import Adw, Gtk


class TestWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.set_title("Power Scheduler Theme Test")
        self.set_default_size(560, 260)
        self.set_resizable(True)

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header_bar = Adw.HeaderBar()
        header_bar.set_show_start_title_buttons(True)
        header_bar.set_show_end_title_buttons(True)
        header_bar.set_title_widget(
            Adw.WindowTitle(
                title="Theme Test",
                subtitle="Minimal libadwaita runtime check",
            )
        )
        toolbar_view.add_top_bar(header_bar)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(760)
        toolbar_view.set_content(clamp)

        page_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=18,
            margin_bottom=18,
            margin_start=18,
            margin_end=18,
        )
        clamp.set_child(page_box)

        title = Gtk.Label()
        title.set_markup("<span size='18000' weight='bold'>Runtime theme probe</span>")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        page_box.append(title)

        subtitle = Gtk.Label(
            label=(
                "Change the system theme while this window is open. "
                "If this window changes visually, the runtime is working."
            )
        )
        subtitle.set_wrap(True)
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_xalign(0.0)
        subtitle.add_css_class("dim-label")
        page_box.append(subtitle)

        controls_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        page_box.append(controls_row)

        suggested_button = Gtk.Button(label="Suggested Action")
        suggested_button.add_css_class("suggested-action")
        controls_row.append(suggested_button)

        normal_button = Gtk.Button(label="Normal Button")
        controls_row.append(normal_button)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Sample entry")
        page_box.append(entry)

        frame = Gtk.Frame()
        page_box.append(frame)

        frame_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        frame.set_child(frame_box)

        self.status_label = Gtk.Label(label="")
        self.status_label.set_wrap(True)
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_xalign(0.0)
        frame_box.append(self.status_label)

    def update_theme_status(self, is_dark: bool, reason: str) -> None:
        self.status_label.set_text(f"reason={reason} | dark={is_dark}")
        self.queue_draw()
        self.queue_resize()


class TestApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="local.power.scheduler.testwindow")
        self.connect("activate", self._on_activate)
        self._style_manager: Adw.StyleManager | None = None

    def _on_activate(self, _app) -> None:
        window = self.props.active_window
        if window is None:
            window = TestWindow(application=self)

        self._ensure_theme_signals(window)
        window.present()

    def _ensure_theme_signals(self, window: TestWindow) -> None:
        if self._style_manager is not None:
            return

        style_manager = self.get_style_manager()
        style_manager.connect("notify::dark", self._on_dark_changed, window)
        self._style_manager = style_manager

        is_dark = bool(style_manager.get_dark())
        print(f"[main_test_window] reason=initial | dark={is_dark}")
        window.update_theme_status(is_dark, "initial")

    def _on_dark_changed(
        self,
        style_manager: Adw.StyleManager,
        _pspec,
        window: TestWindow,
    ) -> None:
        is_dark = bool(style_manager.get_dark())
        print(f"[main_test_window] reason=dark-changed | dark={is_dark}")
        window.update_theme_status(is_dark, "dark-changed")


def main() -> int:
    app = TestApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())