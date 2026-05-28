"""
Worker runner — Celery app for background tasks.
Start with: celery -A app.workers.runner worker --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "careeros",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.analysis_worker", "app.workers.insight_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.analysis_worker.*": {"queue": "analysis"},
        "app.workers.insight_worker.*": {"queue": "insights"},
    },
)

# ── Periodic tasks ────────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Generate weekly insights for all active users — Sunday 8am UTC
    "weekly-insights": {
        "task": "app.workers.insight_worker.generate_insights_for_all_users",
        "schedule": crontab(hour=8, minute=0, day_of_week=0),
    },
    # Send weekly digest emails — Monday 9am UTC
    "weekly-digest": {
        "task": "app.workers.insight_worker.send_weekly_digests",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    # Detect ghosting (apps with no activity 14+ days) — daily 6am
    "ghosting-detection": {
        "task": "app.workers.insight_worker.detect_ghosting",
        "schedule": crontab(hour=6, minute=0),
    },
    # Send follow-up reminders — daily 8am
    "follow-up-reminders": {
        "task": "app.workers.insight_worker.send_follow_up_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    # Compute weekly analytics snapshots — Sunday midnight
    # Send resume fix reminders — daily 10am
    "resume-fix-reminders": {
        "task": "app.workers.insight_worker.send_resume_fix_reminders",
        "schedule": crontab(hour=10, minute=0),
    },
    "weekly-analytics": {
        "task": "app.workers.insight_worker.compute_weekly_analytics",
        "schedule": crontab(hour=0, minute=0, day_of_week=0),
    },
}
