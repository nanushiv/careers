"""
Admin endpoints — manual triggers for scheduled jobs. Protected by admin email check.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.core.config import is_admin
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def require_admin(current_user: dict = Depends(get_current_user)):
    if not is_admin(current_user.get("email", "")):
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


@router.post("/trigger/weekly-digest", summary="Trigger weekly digest emails now")
async def trigger_weekly_digest(admin=Depends(require_admin)):
    from app.workers.insight_worker import _send_digests
    try:
        await _send_digests()
        return {"success": True, "message": "Weekly digest sent to all users"}
    except Exception as e:
        logger.error(f"Manual digest trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/follow-up-reminders", summary="Trigger follow-up reminder emails now")
async def trigger_follow_ups(admin=Depends(require_admin)):
    from app.workers.insight_worker import _send_follow_ups
    await _send_follow_ups()
    return {"success": True, "message": "Follow-up reminders sent"}


@router.post("/trigger/resume-fix-reminders", summary="Trigger resume fix reminder emails now")
async def trigger_resume_fix(admin=Depends(require_admin)):
    from app.workers.insight_worker import _send_resume_fix_reminders
    await _send_resume_fix_reminders()
    return {"success": True, "message": "Resume fix reminders sent"}


@router.get("/users/quota", summary="List all users with their current quota")
async def list_quotas(admin=Depends(require_admin)):
    from app.core.database import supabase
    rows = supabase.table("usage_quotas").select(
        "user_id, analyses_used, analyses_limit, users(email, full_name, plan)"
    ).execute()
    return {"success": True, "data": rows.data or []}
