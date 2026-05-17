from __future__ import annotations

from gi.repository import Gtk


class StatusPanel(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        self.set_size_request(280, -1)
        self.set_valign(Gtk.Align.START)

        self._summary_label: Gtk.Label = Gtk.Label(label="")
        self._status_buffer: Gtk.TextBuffer = Gtk.TextBuffer()
        self._status_text_view: Gtk.TextView = Gtk.TextView.new_with_buffer(
            self._status_buffer
        )

        self._build()

    def _build(self) -> None:
        summary_frame = Gtk.Frame()
        summary_frame.add_css_class("card")
        summary_frame.add_css_class("status-card")
        self.append(summary_frame)

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

        self._summary_label.set_wrap(True)
        self._summary_label.set_halign(Gtk.Align.START)
        self._summary_label.set_xalign(0.0)
        summary_box.append(self._summary_label)

        status_frame = Gtk.Frame()
        status_frame.add_css_class("card")
        status_frame.add_css_class("status-card")
        self.append(status_frame)

        status_outer_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        status_frame.set_child(status_outer_box)

        status_title = Gtk.Label()
        status_title.set_markup("<span weight='bold'>Status</span>")
        status_title.set_halign(Gtk.Align.START)
        status_title.set_xalign(0.0)
        status_outer_box.append(status_title)

        status_scroll = Gtk.ScrolledWindow()
        status_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        status_scroll.set_min_content_height(120)
        status_scroll.set_max_content_height(180)
        status_scroll.set_propagate_natural_height(False)
        status_scroll.set_has_frame(False)
        status_outer_box.append(status_scroll)

        self._status_text_view.set_editable(False)
        self._status_text_view.set_cursor_visible(False)
        self._status_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._status_text_view.set_left_margin(0)
        self._status_text_view.set_right_margin(0)
        self._status_text_view.set_top_margin(0)
        self._status_text_view.set_bottom_margin(0)
        self._status_text_view.add_css_class("dim-label")
        status_scroll.set_child(self._status_text_view)

        self.set_status_content("Choose an action and a delay, then schedule it.", "")

        hints_frame = Gtk.Frame()
        hints_frame.add_css_class("card")
        hints_frame.add_css_class("status-card")
        self.append(hints_frame)

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

    def set_summary(self, text: str) -> None:
        self._summary_label.set_text(text)

    def set_status_content(self, status_text: str, command_text: str | None) -> None:
        clean_status = status_text.strip()
        clean_command = (command_text or "").strip()

        if clean_status and clean_command:
            combined = f"{clean_status}\n\n{clean_command}"
        elif clean_status:
            combined = clean_status
        elif clean_command:
            combined = clean_command
        else:
            combined = ""

        self._status_buffer.set_text(combined)
