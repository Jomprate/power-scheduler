from __future__ import annotations

import atexit
import os
import shutil
import sys
from pathlib import Path

APP_RUNTIME_CONFIG_DIR = (
    Path.home()
    / ".cache"
    / "power-scheduler"
    / "runtime-config"
)


def _prepare_isolated_gtk_config() -> None:
    """
    Force this app to use an isolated XDG config root so GTK4 does not inherit
    user overrides such as ~/.config/gtk-4.0/gtk.css that can break hot theme
    switching in this environment.

    This must run before importing gi / Gtk / Adw.
    """
    runtime_config_dir = APP_RUNTIME_CONFIG_DIR
    gtk_config_dir = runtime_config_dir / "gtk-4.0"

    runtime_config_dir.mkdir(parents=True, exist_ok=True)
    gtk_config_dir.mkdir(parents=True, exist_ok=True)

    os.environ["XDG_CONFIG_HOME"] = str(runtime_config_dir)


def _cleanup_runtime_config() -> None:
    """
    Keep the runtime config disposable for direct main.py launches.
    If in the future you want persistent per-app config, remove this cleanup.
    """
    try:
        shutil.rmtree(APP_RUNTIME_CONFIG_DIR, ignore_errors=True)
    except Exception:
        pass


_prepare_isolated_gtk_config()
atexit.register(_cleanup_runtime_config)

import gi

gi.require_version("Gtk", "4.0")  # type: ignore
gi.require_version("Adw", "1")  # type: ignore

from gi.repository import Adw

from app.application import PowerSchedulerApplication


def main() -> int:
    Adw.init()
    app = PowerSchedulerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())