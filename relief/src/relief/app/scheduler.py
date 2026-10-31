"""Background check that turns due reminders into visible notices (the UI polls /reminders?state=due)."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from relief.app.db import Database


def start(db: Database, every_seconds: int = 60) -> BackgroundScheduler:
    s = BackgroundScheduler(timezone="UTC")
    s.add_job(db.fire_due_reminders, "interval", seconds=every_seconds, id="reminders", max_instances=1, coalesce=True)
    s.start()
    return s
