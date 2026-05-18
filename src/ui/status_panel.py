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
        self.append(self._build_summary_card())
        self.append(self._build_status_card())
        self.set_status_content("Choose an action and a delay, then schedule it.", "")
        self.append(self._build_hints_card())

    def _build_summary_card(self) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.add_css_class("status-card")

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        frame.set_child(box)

        title = Gtk.Label()
        title.set_markup("<span weight='bold'>Summary</span>")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        box.append(title)

        self._summary_label.set_wrap(True)
        self._summary_label.set_halign(Gtk.Align.START)
        self._summary_label.set_xalign(0.0)
        box.append(self._summary_label)

        return frame

    def _build_status_card(self) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.add_css_class("status-card")

        outer_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        frame.set_child(outer_box)

        title = Gtk.Label()
        title.set_markup("<span weight='bold'>Status</span>")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        outer_box.append(title)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(120)
        scroll.set_max_content_height(180)
        scroll.set_propagate_natural_height(False)
        scroll.set_has_frame(False)
        outer_box.append(scroll)

        self._status_text_view.set_editable(False)
        self._status_text_view.set_cursor_visible(False)
        self._status_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._status_text_view.set_left_margin(0)
        self._status_text_view.set_right_margin(0)
        self._status_text_view.set_top_margin(0)
        self._status_text_view.set_bottom_margin(0)
        self._status_text_view.add_css_class("dim-label")
        scroll.set_child(self._status_text_view)

        return frame

    def _build_hints_card(self) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.add_css_class("status-card")

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=14,
            margin_bottom=14,
            margin_start=14,
            margin_end=14,
        )
        frame.set_child(box)

        title = Gtk.Label()
        title.set_markup("<span weight='bold'>Notes</span>")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        box.append(title)

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
        box.append(hints_text)

        return frame

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
