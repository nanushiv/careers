"""
Applications API — intelligent job application tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import logging

from app.core.security import get_current_user
from app.core.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Models ────────────────────────────────────────────────────────────────────

class CreateApplicationRequest(BaseModel):
    company_name: str
    role_title: str
    role_category: Optional[str] = None
    role_level: Optional[str] = None
    job_url: Optional[str] = None
    applied_date: Optional[date] = None
    application_source: str = "unknown"
    resume_id: Optional[str] = None
    jd_id: Optional[str] = None
    has_referral: bool = False
    referral_contact: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    notes: Optional[str] = None
    is_dream_role: bool = False
    priority: str = "medium"


class UpdateApplicationRequest(BaseModel):
    stage: Optional[str] = None
    outcome: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    offered_salary: Optional[int] = None
    next_follow_up_date: Optional[date] = None
    priority: Optional[str] = None


class AddEventRequest(BaseModel):
    event_type: str
    event_date: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None


class CreateFollowUpRequest(BaseModel):
    due_date: date
    follow_up_type: str = "email"
    message_draft: Optional[str] = None


def api_response(data=None, error=None):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


def get_user_id(current_user: dict) -> str:
    resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    return resp.data["id"]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
async def create_application(
    request: CreateApplicationRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    # Check quota for free users
    user_resp = supabase.table("users").select("plan").eq("id", user_id).single().execute()
    if user_resp.data and user_resp.data["plan"] == "free":
        quota_resp = supabase.table("usage_quotas").select("*").eq("user_id", user_id).single().execute()
        quota = quota_resp.data
        if quota and quota["applications_used"] >= quota["applications_limit"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "APPLICATION_QUOTA_EXCEEDED",
                    "message": f"Free plan allows tracking {quota['applications_limit']} applications. Upgrade to Pro for unlimited.",
                    "upgrade_url": "/pricing",
                },
            )

    data = {
        "user_id": user_id,
        **request.model_dump(exclude_none=True),
    }
    if request.applied_date:
        data["applied_date"] = request.applied_date.isoformat()

    resp = supabase.table("applications").insert(data).execute()

    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create application")

    app = resp.data[0]

    # Log "applied" event
    supabase.table("application_events").insert({
        "application_id": app["id"],
        "user_id": user_id,
        "event_type": "applied",
        "description": f"Applied to {request.role_title} at {request.company_name}",
        "metadata": {"source": request.application_source},
    }).execute()

    # Auto-create follow-up reminder (7 days from today)
    from datetime import datetime, timedelta
    follow_up_date = (datetime.now() + timedelta(days=7)).date().isoformat()
    supabase.table("follow_ups").insert({
        "user_id": user_id,
        "application_id": app["id"],
        "due_date": follow_up_date,
        "follow_up_type": "check_status",
        "message_draft": f"Hi, I wanted to follow up on my application for the {request.role_title} role at {request.company_name}. I remain very interested in this opportunity and would love to hear about next steps.",
    }).execute()

    return api_response(data=app)


@router.get("")
async def list_applications(
    stage: Optional[str] = None,
    source: Optional[str] = None,
    role_category: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    query = supabase.table("applications").select(
        "*, resumes(version_label, file_name), job_descriptions(role_category, company_name)"
    ).eq("user_id", user_id).is_("deleted_at", "null").order(
        "created_at", desc=True
    ).limit(limit).offset(offset)

    if stage:
        query = query.eq("stage", stage)
    if source:
        query = query.eq("application_source", source)
    if role_category:
        query = query.eq("role_category", role_category)

    resp = query.execute()
    return api_response(data=resp.data)


@router.get("/{app_id}")
async def get_application(
    app_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    app_resp = supabase.table("applications").select("*").eq(
        "id", app_id
    ).eq("user_id", user_id).single().execute()

    if not app_resp.data:
        raise HTTPException(status_code=404, detail="Application not found")

    # Fetch related data
    events = supabase.table("application_events").select("*").eq(
        "application_id", app_id
    ).order("event_date", desc=True).execute()

    interviews = supabase.table("interviews").select("*").eq(
        "application_id", app_id
    ).execute()

    follow_ups = supabase.table("follow_ups").select("*").eq(
        "application_id", app_id
    ).eq("status", "pending").order("due_date").execute()

    return api_response(data={
        "application": app_resp.data,
        "events": events.data,
        "interviews": interviews.data,
        "follow_ups": follow_ups.data,
    })


@router.patch("/{app_id}")
async def update_application(
    app_id: str,
    request: UpdateApplicationRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    # Fetch current state to detect stage change
    current = supabase.table("applications").select("stage").eq(
        "id", app_id
    ).eq("user_id", user_id).single().execute()

    if not current.data:
        raise HTTPException(status_code=404, detail="Application not found")

    update_data = request.model_dump(exclude_none=True)
    if request.next_follow_up_date:
        update_data["next_follow_up_date"] = request.next_follow_up_date.isoformat()

    resp = supabase.table("applications").update(update_data).eq(
        "id", app_id
    ).eq("user_id", user_id).execute()

    # Log stage change event
    if request.stage and request.stage != current.data.get("stage"):
        supabase.table("application_events").insert({
            "application_id": app_id,
            "user_id": user_id,
            "event_type": "stage_advanced",
            "description": f"Stage updated: {current.data['stage']} → {request.stage}",
            "metadata": {
                "stage_from": current.data["stage"],
                "stage_to": request.stage,
            },
        }).execute()

        # Auto-update last_stage_change_at
        supabase.table("applications").update({
            "last_stage_change_at": "NOW()",
        }).eq("id", app_id).execute()

    return api_response(data=resp.data[0] if resp.data else {})


@router.delete("/{app_id}")
async def delete_application(
    app_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)
    supabase.table("applications").update({
        "deleted_at": "NOW()"
    }).eq("id", app_id).eq("user_id", user_id).execute()
    return api_response(data={"deleted": True})


@router.post("/{app_id}/events")
async def add_event(
    app_id: str,
    request: AddEventRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)
    resp = supabase.table("application_events").insert({
        "application_id": app_id,
        "user_id": user_id,
        "event_type": request.event_type,
        "event_date": request.event_date or "NOW()",
        "description": request.description,
        "metadata": request.metadata or {},
    }).execute()
    return api_response(data=resp.data[0] if resp.data else {})


@router.get("/{app_id}/events")
async def get_events(
    app_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)
    resp = supabase.table("application_events").select("*").eq(
        "application_id", app_id
    ).eq("user_id", user_id).order("event_date", desc=True).execute()
    return api_response(data=resp.data)


@router.post("/{app_id}/follow-ups")
async def create_follow_up(
    app_id: str,
    request: CreateFollowUpRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)
    resp = supabase.table("follow_ups").insert({
        "user_id": user_id,
        "application_id": app_id,
        "due_date": request.due_date.isoformat(),
        "follow_up_type": request.follow_up_type,
        "message_draft": request.message_draft,
    }).execute()
    return api_response(data=resp.data[0] if resp.data else {})
