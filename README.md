# Power Scheduler

Simple Linux desktop app for scheduling:

- Lock
- Log out
- Suspend
- Hibernate
- Power off

The app schedules the action through systemd, so it does not need to remain open.

## Run

```bash
PYTHONPATH=src python3 src/main.py