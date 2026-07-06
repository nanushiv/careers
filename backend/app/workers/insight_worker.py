"""
Insight Worker — scheduled Celery tasks: insights, digests, ghosting detection, follow-ups.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from app.workers.runner import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def generate_insights_for_all_users():
    asyncio.run(_generate_all_insights())


@celery_app.task
def send_weekly_digests():
    asyncio.run(_send_digests())


@celery_app.task
def detect_ghosting():
    asyncio.run(_detect_ghosting())


@celery_app.task
def send_follow_up_reminders():
    asyncio.run(_send_follow_ups())


@celery_app.task
def compute_weekly_analytics():
    asyncio.run(_compute_analytics())


async def _generate_all_insights():
    from app.core.database import supabase
    from app.services.insights.insight_engine import insight_engine

    users = supabase.table("users").select("id").is_("deleted_at", "null").execute().data or []
    for user in users:
        try:
            await insight_engine.generate_weekly_insights(user["id"])
        except Exception as e:
            logger.error(f"Insights failed for {user['id']}: {e}")


async def _detect_ghosting():
    """Mark applications as ghosted if no activity in 14+ days and still in early stage."""
    from app.core.database import supabase

    cutoff = (datetime.utcnow() - timedelta(days=14)).isoformat()
    early_stages = ["applied", "screening"]

    stale = supabase.table("applications").select("id, user_id, company_name, role_title").in_(
        "stage", early_stages
    ).lt("last_stage_change_at", cutoff).is_("deleted_at", "null").execute().data or []

    for app in stale:
        supabase.table("applications").update({"stage": "ghosted"}).eq("id", app["id"]).execute()
        supabase.table("application_events").insert({
            "application_id": app["id"],
            "user_id": app["user_id"],
            "event_type": "ghosted_detected",
            "description": f"No response from {app['company_name']} in 14+ days. Marked as ghosted.",
        }).execute()

    logger.info(f"Ghosting detection: {len(stale)} applications marked ghosted")


async def _send_follow_ups():
    """Email follow-up reminders for due today."""
    from app.core.database import supabase
    from app.services.notifications.email import send_follow_up_reminder

    today = datetime.utcnow().date().isoformat()

    due = supabase.table("follow_ups").select(
        "*, applications(company_name, role_title), users(email, full_name)"
    ).eq("status", "pending").eq("due_date", today).execute().data or []

    for fu in due:
        try:
            user = fu.get("users", {})
            app = fu.get("applications", {})
            await send_follow_up_reminder(
                to_email=user.get("email", ""),
                user_name=user.get("full_name", ""),
                company_name=app.get("company_name", ""),
                role_title=app.get("role_title", ""),
                draft_message=fu.get("message_draft"),
            )
        except Exception as e:
            logger.error(f"Follow-up email failed: {e}")


async def _send_digests():
    from app.core.database import supabase
    from app.services.notifications.email import send_weekly_digest
    from app.api.v1.dashboard import _compute_career_health

    users = supabase.table("users").select("id, email, full_name").is_(
        "deleted_at", "null"
    ).execute().data or []

    for user in users:
        try:
            if not user.get("email"):
                continue

            all_apps = supabase.table("applications").select("stage, applied_date").eq(
                "user_id", user["id"]
            ).is_("deleted_at", "null").execute().data or []

            active_apps = [a for a in all_apps if a["stage"] not in ("rejected", "ghosted", "withdrawn")]
            callbacks = [a for a in all_apps if a["stage"] not in ("applied", "rejected", "ghosted")]
            callback_rate = round(len(callbacks) / len(all_apps) * 100, 1) if all_apps else 0
            health_score = _compute_career_health(
                total_apps=len(all_apps),
                callback_rate=callback_rate,
                active_pipeline=len(active_apps),
                has_interviews=any(a["stage"] in ("technical", "case_study", "final") for a in all_apps),
                has_offers=any(a["stage"] == "offer" for a in all_apps),
                ghost_rate=len([a for a in all_apps if a["stage"] == "ghosted"]) / max(len(all_apps), 1) * 100,
            )

            insights = supabase.table("ai_insights").select("title, summary").eq(
                "user_id", user["id"]
            ).eq("is_dismissed", False).order("created_at", desc=True).limit(3).execute().data or []

            follow_ups = supabase.table("follow_ups").select("id").eq(
                "user_id", user["id"]
            ).eq("status", "pending").execute().data or []

            week_start = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
            week_apps = supabase.table("applications").select("id").eq(
                "user_id", user["id"]
            ).gte("applied_date", week_start).execute().data or []

            await send_weekly_digest(
                to_email=user["email"],
                user_name=user.get("full_name", ""),
                career_health_score=health_score,
                new_insights=insights,
                follow_ups_due=len(follow_ups),
                week_apps=len(week_apps),
            )
        except Exception as e:
            logger.error(f"Digest failed for {user['id']}: {e}")


async def _compute_analytics():
    from app.services.analytics.aggregator import aggregator
    await aggregator.compute_for_all_users()


@celery_app.task
def send_resume_fix_reminders():
    asyncio.run(_send_resume_fix_reminders())


async def _send_resume_fix_reminders():
    """
    3 days after analysis, if score < 60 and no new resume uploaded,
    send a fix reminder email.
    """
    from app.core.database import supabase
    from app.services.notifications.email import send_resume_fix_reminder
    from datetime import datetime, timedelta

    three_days_ago = (datetime.utcnow() - timedelta(days=3)).isoformat()
    four_days_ago = (datetime.utcnow() - timedelta(days=4)).isoformat()

    # Analyses done 3 days ago with low score
    analyses = supabase.table("resume_analyses").select(
        "*, users(email, full_name), resumes(id, created_at)"
    ).eq("analysis_type", "ats").lt(
        "overall_score", 60
    ).gte("created_at", four_days_ago).lte("created_at", three_days_ago).execute().data or []

    for a in analyses:
        user = a.get("users", {})
        resume = a.get("resumes", {})
        if not user.get("email"):
            continue

        # Check if they uploaded a new resume since analysis
        newer_resume = supabase.table("resumes").select("id").eq(
            "user_id", a["user_id"]
        ).gte("created_at", a["created_at"]).is_("deleted_at", "null").execute().data

        if newer_resume:
            continue  # Already re-uploaded — skip

        gaps = [g.get("description", "") for g in (a.get("gaps") or [])[:3]]

        await send_resume_fix_reminder(
            to_email=user["email"],
            user_name=user.get("full_name", "there"),
            ats_score=a.get("overall_score", 0),
            top_gaps=gaps,
            resume_id=a["resume_id"],
        )
