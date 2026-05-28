"""
Outreach API — generate personalized cold emails. Pro only.
Never auto-sends — user always reviews first.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.core.security import get_current_user
from app.core.database import supabase
from app.services.outreach.generator import outreach_service

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateEmailRequest(BaseModel):
    recipient_name: str
    recipient_title: str
    company_name: str
    goal: str = "informational_interview"
    context: Optional[str] = None


class BulkGenerateRequest(BaseModel):
    recipients: List[dict]
    goal: str = "informational_interview"


class CreateOutreachReminderRequest(BaseModel):
    recipient_name: str
    company: str
    goal: str
    email_subject: str
    days_until_followup: int = 5  # default: follow up in 5 days


def api_response(data=None, error=None):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


def get_user(current_user):
    resp = supabase.table("users").select("*").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    return resp.data[0]


def require_pro(user: dict):
    if user.get("plan", "free") == "free":
        raise HTTPException(
            status_code=402,
            detail={
                "code": "PRO_REQUIRED",
                "message": "Outreach email generation is a Pro feature.",
                "upgrade_url": "/pricing",
            },
        )


@router.post("/generate")
async def generate_outreach_email(
    request: GenerateEmailRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate one personalized outreach email."""
    user = get_user(current_user)
    require_pro(user)

    # Get resume strengths from latest analysis
    latest_analysis = supabase.table("resume_analyses").select(
        "strengths"
    ).eq("user_id", user["id"]).eq("analysis_type", "ats").order(
        "created_at", desc=True
    ).limit(1).execute()

    strengths = []
    if latest_analysis.data:
        raw = latest_analysis.data[0].get("strengths", [])
        strengths = [s.get("area", "") for s in raw if s.get("area")]

    result = await outreach_service.generate_email(
        sender_name=user.get("full_name", ""),
        current_role=user.get("current_title", ""),
        target_role=(user.get("target_roles") or ["Product Manager"])[0],
        key_strengths=strengths,
        recipient_name=request.recipient_name,
        recipient_title=request.recipient_title,
        company_name=request.company_name,
        goal=request.goal,
        context=request.context or "",
        user_id=user["id"],
        user_plan=user.get("plan", "free"),
    )

    return api_response(data=result.to_dict())


@router.post("/bulk-generate")
async def bulk_generate(
    request: BulkGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate personalized emails for multiple recipients at once."""
    user = get_user(current_user)
    require_pro(user)

    if len(request.recipients) > 10:
        raise HTTPException(status_code=400, detail="Max 10 recipients per bulk request.")

    latest_analysis = supabase.table("resume_analyses").select(
        "strengths"
    ).eq("user_id", user["id"]).order("created_at", desc=True).limit(1).execute()

    strengths = []
    if latest_analysis.data:
        raw = latest_analysis.data[0].get("strengths", [])
        strengths = [s.get("area", "") for s in raw if s.get("area")]

    sender_profile = {
        "name": user.get("full_name", ""),
        "current_role": user.get("current_title", ""),
        "target_role": (user.get("target_roles") or ["Product Manager"])[0],
        "key_strengths": strengths,
    }

    results = await outreach_service.generate_bulk(
        sender_profile=sender_profile,
        recipients=request.recipients,
        goal=request.goal,
        user_id=user["id"],
        user_plan=user.get("plan", "free"),
    )

    return api_response(data={"emails": results, "count": len(results)})


@router.post("/reminders")
async def create_outreach_reminder(
    request: CreateOutreachReminderRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save a follow-up reminder for a sent outreach email."""
    user = get_user(current_user)

    due_date = (datetime.now() + timedelta(days=request.days_until_followup)).date().isoformat()
    label = f"{request.recipient_name} · {request.company}"
    draft_body = f'Hi {request.recipient_name}, just wanted to follow up on my previous message. Would you be open to a quick chat?'
    # First line of message_draft used as display label in notification bell
    message_draft = f"{label}\n\nRe: {request.email_subject}\n\n{draft_body}"

    resp = supabase.table("follow_ups").insert({
        "user_id": user["id"],
        "application_id": None,
        "due_date": due_date,
        "follow_up_type": "email",
        "message_draft": message_draft,
        "status": "pending",
    }).execute()

    return api_response(data=resp.data[0] if resp.data else {"due_date": due_date})


@router.get("/contact-suggestions")
async def get_contact_suggestions_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """AI-generated contact archetypes for outreach targeting. Pro only."""
    user = get_user(current_user)
    require_pro(user)

    resume_resp = supabase.table("resumes").select("raw_text").eq(
        "user_id", user["id"]
    ).eq("is_primary", True).is_("deleted_at", "null").limit(1).execute()

    resume_text = ""
    if resume_resp.data:
        resume_text = resume_resp.data[0].get("raw_text", "") or ""

    from app.services.outreach.contact_suggestions import get_contact_suggestions

    contacts = await get_contact_suggestions(
        resume_text=resume_text,
        target_roles=user.get("target_roles") or ["Product Manager"],
        user_name=user.get("full_name", ""),
        current_title=user.get("current_title", ""),
    )

    return api_response(data={"contacts": contacts})


@router.patch("/reminders/{reminder_id}/done")
async def mark_reminder_done(
    reminder_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Mark a follow-up reminder as completed."""
    user = get_user(current_user)

    supabase.table("follow_ups").update({
        "status": "completed"
    }).eq("id", reminder_id).eq("user_id", user["id"]).execute()

    return api_response(data={"done": True})
