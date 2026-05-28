"""
Analytics Aggregator — computes weekly snapshots stored in user_analytics table.
Run by the weekly Celery beat task.
"""
import logging
from datetime import datetime, timedelta

from app.core.database import supabase

logger = logging.getLogger(__name__)


class AnalyticsAggregator:

    async def compute_weekly_snapshot(self, user_id: str):
        """Compute and store a weekly analytics snapshot for one user."""
        now = datetime.utcnow()
        week_start = (now - timedelta(days=now.weekday())).date()

        apps = supabase.table("applications").select("*").eq(
            "user_id", user_id
        ).is_("deleted_at", "null").execute().data or []

        week_apps = [
            a for a in apps
            if a.get("applied_date", "") >= str(week_start)
        ]

        # Source breakdown
        apps_by_source: dict = {}
        for app in week_apps:
            src = app.get("application_source", "unknown")
            apps_by_source[src] = apps_by_source.get(src, 0) + 1

        # Category breakdown
        apps_by_category: dict = {}
        for app in apps:
            cat = app.get("role_category", "Other") or "Other"
            apps_by_category[cat] = apps_by_category.get(cat, 0) + 1

        # Stage distribution
        stage_dist: dict = {}
        for app in apps:
            s = app.get("stage", "applied")
            stage_dist[s] = stage_dist.get(s, 0) + 1

        # Callback rate
        callbacks = [a for a in apps if a["stage"] not in ("applied", "rejected", "ghosted")]
        callback_rate = round(len(callbacks) / max(len(apps), 1) * 100, 1)

        # Screenings this week
        screenings = [
            a for a in apps
            if a["stage"] != "applied"
            and a.get("last_stage_change_at", "") >= str(week_start)
        ]

        snapshot = {
            "user_id": user_id,
            "week_start": str(week_start),
            "apps_submitted": len(week_apps),
            "apps_by_source": apps_by_source,
            "apps_by_category": apps_by_category,
            "screenings_received": len(screenings),
            "callback_rate": callback_rate,
            "ghosted_count": len([a for a in apps if a["stage"] == "ghosted"]),
            "stage_distribution": stage_dist,
        }

        # Upsert (update if week already exists)
        supabase.table("user_analytics").upsert(
            snapshot, on_conflict="user_id,week_start"
        ).execute()

        logger.info(f"Weekly snapshot computed for user {user_id}")
        return snapshot

    async def compute_for_all_users(self):
        """Run weekly snapshots for all active users."""
        users = supabase.table("users").select("id").is_("deleted_at", "null").execute().data or []
        for user in users:
            try:
                await self.compute_weekly_snapshot(user["id"])
            except Exception as e:
                logger.error(f"Snapshot failed for {user['id']}: {e}")


aggregator = AnalyticsAggregator()
