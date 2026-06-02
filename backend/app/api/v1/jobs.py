"""
Jobs API — AI-powered job suggestions matched to user's resume.
Premium feature (Pro plan only).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from app.core.security import get_current_user
from app.core.database import supabase
from app.core.config import is_admin
from app.services.jobs.suggestions import job_suggestions_service

logger = logging.getLogger(__name__)
router = APIRouter()


def api_response(data=None, error=None):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


@router.get("/suggestions")
async def get_job_suggestions(
    location: str = Query(default="Remote"),
    limit: int = Query(default=20, le=50),
    current_user: dict = Depends(get_current_user),
):
    """Get AI-matched job suggestions based on resume. Pro only."""
    user_resp = supabase.table("users").select("*").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_resp.data[0]

    # Gate behind Pro plan (admin bypass)
    if user.get("plan", "free") == "free" and not is_admin(user.get("email", "")):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "PRO_REQUIRED",
                "message": "Job suggestions are a Pro feature. Upgrade to unlock.",
                "upgrade_url": "/pricing",
            },
        )

    # Get primary resume
    resume_resp = supabase.table("resumes").select("raw_text").eq(
        "user_id", user["id"]
    ).eq("is_primary", True).is_("deleted_at", "null").limit(1).execute()

    if not resume_resp.data or not resume_resp.data[0].get("raw_text"):
        raise HTTPException(
            status_code=400,
            detail="Please upload and analyze your resume first."
        )

    target_roles = user.get("target_roles", [])
    if not target_roles:
        raise HTTPException(
            status_code=400,
            detail="Please set your target roles in Settings first."
        )

    suggestions = await job_suggestions_service.get_suggestions(
        resume_text=resume_resp.data[0]["raw_text"],
        target_roles=target_roles,
        location=location or user.get("location", "Remote"),
        limit=limit,
        user_id=user["id"],
    )

    return api_response(data={
        "jobs": suggestions,
        "total": len(suggestions),
        "target_roles": target_roles,
        "location": location,
    })


@router.post("/save/{job_id}")
async def save_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Save a job to applications tracker."""
    # This would create an application record from a job suggestion
    return api_response(data={"saved": True, "job_id": job_id})
