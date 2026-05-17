from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gi.repository import Adw

from services.palette_service import PaletteService


def _make_service() -> PaletteService:
    app = Adw.Application(application_id="test.test_palette")
    return PaletteService(app)


class BuildPaletteCssTests(unittest.TestCase):
    def test_returns_empty_when_no_palette_and_no_user_css(self) -> None:
        service = _make_service()

        with (
            patch.object(service, "_get_preferred_palette", return_value=None),
            patch.object(service, "_get_user_css", return_value=None),
        ):
            result = service._build_palette_css()

        self.assertEqual(result, "")

    def test_returns_empty_when_palette_file_does_not_exist(self) -> None:
        service = _make_service()
        fake_path = Path("/nonexistent/palette.css")

        with (
            patch.object(service, "_get_preferred_palette", return_value=fake_path),
            patch.object(service, "_get_user_css", return_value=None),
        ):
            result = service._build_palette_css()

        self.assertEqual(result, "")

    def test_returns_empty_when_fallback_does_not_exist(self) -> None:
        service = _make_service()

        with (
            patch.object(service, "_get_preferred_palette", return_value=None),
            patch.object(
                service, "_get_user_css", return_value=Path("/nonexistent/gtk.css")
            ),
        ):
            result = service._build_palette_css()

        self.assertEqual(result, "")

    def test_returns_empty_when_file_has_no_define_color_rules(self) -> None:
        service = _make_service()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write("body { color: red; }\n")
            css_path = Path(f.name)

        try:
            with (
                patch.object(service, "_get_preferred_palette", return_value=css_path),
            ):
                result = service._build_palette_css()

            self.assertEqual(result, "")
        finally:
            css_path.unlink(missing_ok=True)

    def test_extracts_define_color_rules(self) -> None:
        service = _make_service()
        content = (
            "/* comment */\n"
            "@define-color bg_color #1a1a1a;\n"
            "// inline comment\n"
            "@define-color fg_color #ffffff;\n"
            "body { color: red; }\n"
            "@define-color accent_color #3584e4;\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(content)
            css_path = Path(f.name)

        try:
            with (
                patch.object(service, "_get_preferred_palette", return_value=css_path),
            ):
                result = service._build_palette_css()

            self.assertIn("@define-color bg_color #1a1a1a", result)
            self.assertIn("@define-color fg_color #ffffff", result)
            self.assertIn("@define-color accent_color #3584e4", result)
            self.assertNotIn("body { color: red; }", result)
            self.assertNotIn("/* comment */", result)
            self.assertNotIn("// inline comment", result)
            self.assertTrue(result.startswith("/* Imported system palette */"))
        finally:
            css_path.unlink(missing_ok=True)

    def test_uses_fallback_when_preferred_not_found(self) -> None:
        service = _make_service()
        fallback_content = "@define-color bg_color #000000;\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(fallback_content)
            fallback_path = Path(f.name)

        try:
            with (
                patch.object(service, "_get_preferred_palette", return_value=None),
                patch.object(service, "_get_user_css", return_value=fallback_path),
            ):
                result = service._build_palette_css()

            self.assertIn("@define-color bg_color #000000", result)
        finally:
            fallback_path.unlink(missing_ok=True)


class GetPreferredPaletteTests(unittest.TestCase):
    def test_returns_none_when_cosmic_dir_does_not_exist(self) -> None:
        service = _make_service()

        with (
            patch.object(service._style_manager, "get_dark", return_value=True),
            patch("services.palette_service.Path.exists", return_value=False),
        ):
            result = service._get_preferred_palette()

        self.assertIsNone(result)

    def test_returns_dark_css_when_dark_mode(self) -> None:
        service = _make_service()

        with tempfile.TemporaryDirectory() as tmp:
            cosmic_dir = Path(tmp) / ".config" / "gtk-4.0" / "cosmic"
            cosmic_dir.mkdir(parents=True)
            dark_css = cosmic_dir / "dark.css"
            dark_css.write_text("", encoding="utf-8")

            with (
                patch("services.palette_service.Path.home", return_value=Path(tmp)),
                patch.object(service._style_manager, "get_dark", return_value=True),
            ):
                result = service._get_preferred_palette()

            self.assertIsNotNone(result)
            self.assertEqual(result.name, "dark.css")

    def test_returns_light_css_when_light_mode(self) -> None:
        service = _make_service()

        with tempfile.TemporaryDirectory() as tmp:
            cosmic_dir = Path(tmp) / ".config" / "gtk-4.0" / "cosmic"
            cosmic_dir.mkdir(parents=True)
            light_css = cosmic_dir / "light.css"
            light_css.write_text("", encoding="utf-8")

            with (
                patch("services.palette_service.Path.home", return_value=Path(tmp)),
                patch.object(service._style_manager, "get_dark", return_value=False),
            ):
                result = service._get_preferred_palette()

            self.assertIsNotNone(result)
            self.assertEqual(result.name, "light.css")


class GetUserCssTests(unittest.TestCase):
    def test_returns_path_when_gtk_css_exists(self) -> None:
        service = _make_service()

        with tempfile.TemporaryDirectory() as tmp:
            gtk_dir = Path(tmp) / ".config" / "gtk-4.0"
            gtk_dir.mkdir(parents=True)
            gtk_css = gtk_dir / "gtk.css"
            gtk_css.write_text("", encoding="utf-8")

            with patch("services.palette_service.Path.home", return_value=Path(tmp)):
                result = service._get_user_css()

            self.assertIsNotNone(result)
            self.assertEqual(result.name, "gtk.css")

    def test_returns_none_when_gtk_css_does_not_exist(self) -> None:
        service = _make_service()

        with tempfile.TemporaryDirectory() as tmp:
            with patch("services.palette_service.Path.home", return_value=Path(tmp)):
                result = service._get_user_css()

            self.assertIsNone(result)


class ReadSafeTests(unittest.TestCase):
    def test_returns_content_for_valid_utf8(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("hello world")
            path = Path(f.name)

        try:
            result = PaletteService._read_safe(path)
            self.assertEqual(result, "hello world")
        finally:
            path.unlink(missing_ok=True)

    def test_returns_empty_string_for_non_existent_file(self) -> None:
        result = PaletteService._read_safe(Path("/does/not/exist.css"))
        self.assertEqual(result, "")

    def test_returns_empty_string_when_path_is_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = PaletteService._read_safe(Path(tmp))
            self.assertEqual(result, "")

    def test_handles_binary_content_gracefully(self) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"\x80\x81\x82")
            path = Path(f.name)

        try:
            result = PaletteService._read_safe(path)
            self.assertIsInstance(result, str)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
