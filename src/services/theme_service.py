from __future__ import annotations

import gi

gi.require_version("Adw", "1")  # type: ignore

from collections.abc import Callable

from gi.repository import Adw


ThemeChangedCallback = Callable[[bool], None]


class ThemeService:
    def __init__(self, application: Adw.Application) -> None:
        self._application = application
        self._style_manager: Adw.StyleManager | None = None
        self._callbacks: list[ThemeChangedCallback] = []
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        style_manager = self._application.get_style_manager()

        style_manager.connect("notify::dark", self._on_dark_changed)
        style_manager.connect(
            "notify::high-contrast",
            self._on_high_contrast_changed,
        )
        style_manager.connect(
            "notify::system-supports-color-schemes",
            self._on_system_color_schemes_changed,
        )

        self._style_manager = style_manager
        self._started = True

        self._print_diagnostics("initial")

    def add_theme_changed_callback(
        self,
        callback: ThemeChangedCallback,
    ) -> None:
        self._callbacks.append(callback)

    def get_is_dark(self) -> bool:
        if self._style_manager is None:
            return False

        return bool(self._style_manager.get_dark())

    def _on_dark_changed(self, _style_manager, _pspec) -> None:
        self._print_diagnostics("dark-changed")
        self._emit_theme_changed()

    def _on_high_contrast_changed(self, _style_manager, _pspec) -> None:
        self._print_diagnostics("high-contrast-changed")
        self._emit_theme_changed()

    def _on_system_color_schemes_changed(self, _style_manager, _pspec) -> None:
        self._print_diagnostics("system-supports-color-schemes-changed")
        self._emit_theme_changed()

    def _emit_theme_changed(self) -> None:
        is_dark = self.get_is_dark()

        for callback in self._callbacks:
            callback(is_dark)

    def _print_diagnostics(self, reason: str) -> None:
        if self._style_manager is None:
            return

        style_manager = self._style_manager

        dark = style_manager.get_dark()
        high_contrast = style_manager.get_high_contrast()
        color_scheme = style_manager.get_color_scheme()
        system_supports_color_schemes = (
            style_manager.get_system_supports_color_schemes()
        )

        debug_parts = [
            f"[PowerScheduler][theme] reason={reason}",
            f"dark={dark}",
            f"high_contrast={high_contrast}",
            f"color_scheme={int(color_scheme)}",
            f"system_supports_color_schemes={system_supports_color_schemes}",
        ]

        if hasattr(style_manager, "get_system_supports_accent_colors"):
            try:
                debug_parts.append(
                    "system_supports_accent_colors="
                    f"{style_manager.get_system_supports_accent_colors()}"
                )
            except Exception:
                pass

        if hasattr(style_manager, "get_accent_color"):
            try:
                debug_parts.append(
                    f"accent_color={style_manager.get_accent_color()}"
                )
            except Exception:
                pass

        print(" | ".join(debug_parts))