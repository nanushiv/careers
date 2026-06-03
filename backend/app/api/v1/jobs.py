"""
Jobs API — AI-powered job suggestions matched to user's resume.
Premium feature (Pro plan only).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional
import re
import logging
from datetime import datetime

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
    resume_resp = supabase.table("resumes").select("raw_text, structured_data").eq(
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

    user_yoe = _calc_yoe(resume_resp.data[0].get("structured_data") or {}, resume_resp.data[0].get("raw_text", ""))

    suggestions = await job_suggestions_service.get_suggestions(
        resume_text=resume_resp.data[0]["raw_text"],
        target_roles=target_roles,
        location=location or user.get("location", "Remote"),
        limit=limit,
        user_id=user["id"],
        user_yoe=user_yoe,
    )

    return api_response(data={
        "jobs": suggestions["jobs"],
        "total": len(suggestions["jobs"]),
        "location_note": suggestions["location_note"],
        "user_yoe": user_yoe,
        "target_roles": target_roles,
        "location": location,
    })


def _calc_yoe(structured_data: dict, raw_text: str) -> Optional[int]:
    """Calculate total years of experience from structured resume data or raw text."""
    # Try structured work experience dates first
    experiences = structured_data.get("work_experience") or structured_data.get("experience") or []
    if experiences:
        total_months = 0
        now = datetime.now()
        for exp in experiences:
            if not isinstance(exp, dict):
                continue
            start = exp.get("start_date") or exp.get("from") or ""
            end = exp.get("end_date") or exp.get("to") or "present"
            try:
                s = _parse_date(start)
                e = _parse_date(end) if end.lower() not in ("present", "current", "now") else now
                if s and e and e > s:
                    total_months += (e.year - s.year) * 12 + (e.month - s.month)
            except Exception:
                pass
        if total_months > 0:
            return max(1, round(total_months / 12))

    # Fallback: scan raw text for "X years of experience"
    m = re.search(r'(\d+)\+?\s*years?\s+of\s+(?:total\s+)?(?:professional\s+)?experience', raw_text, re.I)
    if m:
        return int(m.group(1))
    return None


def _parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m", "%b %Y", "%B %Y", "%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


@router.post("/save/{job_id}")
async def save_job(
    job_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Save a job to the applications tracker (creates an application row)."""
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user_resp.data[0]["id"]

    job_url = body.get("url", "")

    # Check if already saved (avoid duplicates by URL)
    if job_url:
        existing = supabase.table("applications").select("id").eq(
            "user_id", user_id
        ).eq("job_url", job_url).limit(1).execute()
        if existing.data:
            return api_response(data={"saved": True, "already_existed": True})

    supabase.table("applications").insert({
        "user_id": user_id,
        "company_name": body.get("company", ""),
        "role_title": body.get("title", ""),
        "stage": "applied",
        "job_url": job_url,
        "notes": f"Saved from Job Matches. Fit score: {body.get('fit_score', '')}%",
        "application_source": "job_board",
    }).execute()

    return api_response(data={"saved": True, "already_existed": False})
