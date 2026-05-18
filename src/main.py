from __future__ import annotations

import atexit
import contextlib
import os
import shutil
import sys
from pathlib import Path

APP_RUNTIME_CONFIG_DIR = Path.home() / ".cache" / "power-scheduler" / "runtime-config"


def _prepare_isolated_gtk_config() -> None:
    runtime_config_dir = APP_RUNTIME_CONFIG_DIR
    gtk_config_dir = runtime_config_dir / "gtk-4.0"

    runtime_config_dir.mkdir(parents=True, exist_ok=True)
    gtk_config_dir.mkdir(parents=True, exist_ok=True)

    os.environ["XDG_CONFIG_HOME"] = str(runtime_config_dir)


def _cleanup_runtime_config() -> None:
    target = APP_RUNTIME_CONFIG_DIR

    # Safety guard: only remove paths that clearly belong to this app.
    if (
        target.exists()
        and target.is_dir()
        and "power-scheduler" in target.resolve().as_posix()
    ):
        with contextlib.suppress(Exception):
            shutil.rmtree(target, ignore_errors=True)


_prepare_isolated_gtk_config()
atexit.register(_cleanup_runtime_config)

import gi

gi.require_version("Gtk", "4.0")  # type: ignore
gi.require_version("Adw", "1")  # type: ignore

from gi.repository import Adw

from app.application import PowerSchedulerApplication
from repositories.scheduled_job_repository import ScheduledJobRepository
from services.capability_service import CapabilityService
from services.notification_service import NotificationService
from services.schedule_controller import ScheduleController
from services.scheduler_service import SchedulerService
from services.session_service import SessionService
from services.shutdown_service import ShutdownService
from services.systemd_service import SystemdService


def main() -> int:
    Adw.init()

    session_service = SessionService()
    shutdown_service = ShutdownService()
    systemd_service = SystemdService()
    scheduled_job_repository = ScheduledJobRepository()
    capability_service = CapabilityService()

    scheduler_service = SchedulerService(
        action_services=[session_service, shutdown_service],
        systemd_service=systemd_service,
        scheduled_job_repository=scheduled_job_repository,
    )

    app = PowerSchedulerApplication(
        controller=ScheduleController(
            scheduler_service=scheduler_service,
        ),
        capability_service=capability_service,
    )

    notification_service = NotificationService(app)
    app.set_notification_service(notification_service)

    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
