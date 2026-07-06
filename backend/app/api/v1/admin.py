"""
Admin endpoints — manual triggers for scheduled jobs.
Trigger endpoints: X-Cron-Secret header (works for cron-job.org and manual curl).
Quota endpoint: Clerk JWT (admin email only).
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from app.core.security import get_current_user
from app.core.config import is_admin, settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def require_cron_secret(x_cron_secret: Optional[str] = Header(default=None)):
    if not settings.ADMIN_CRON_SECRET:
        raise HTTPException(status_code=503, detail="ADMIN_CRON_SECRET not configured on server")
    if x_cron_secret != settings.ADMIN_CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


def require_clerk_admin(current_user: dict = Depends(get_current_user)):
    if not is_admin(current_user.get("email", "")):
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


@router.post("/trigger/weekly-digest", summary="Trigger weekly digest emails now")
async def trigger_weekly_digest(_=Depends(require_cron_secret)):
    from app.workers.insight_worker import _send_digests
    try:
        await _send_digests()
        return {"success": True, "message": "Weekly digest sent to all users"}
    except Exception as e:
        logger.error(f"Manual digest trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/follow-up-reminders", summary="Trigger follow-up reminder emails now")
async def trigger_follow_ups(_=Depends(require_cron_secret)):
    from app.workers.insight_worker import _send_follow_ups
    await _send_follow_ups()
    return {"success": True, "message": "Follow-up reminders sent"}


@router.post("/trigger/resume-fix-reminders", summary="Trigger resume fix reminder emails now")
async def trigger_resume_fix(_=Depends(require_cron_secret)):
    from app.workers.insight_worker import _send_resume_fix_reminders
    await _send_resume_fix_reminders()
    return {"success": True, "message": "Resume fix reminders sent"}


@router.get("/users/quota", summary="List all users with their current quota")
async def list_quotas(admin=Depends(require_clerk_admin)):
    from app.core.database import supabase
    rows = supabase.table("usage_quotas").select(
        "user_id, analyses_used, analyses_limit, users(email, full_name, plan)"
    ).execute()
    return {"success": True, "data": rows.data or []}
