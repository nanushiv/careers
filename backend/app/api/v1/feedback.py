"""
Feedback API — collect and store product feedback + waitlist signups.
No auth required — public endpoint.
"""
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging

from app.core.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    email: str
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    from_role: Optional[str] = None
    target_role: Optional[str] = None
    pain_points: List[str] = []
    biggest_struggle: Optional[str] = None
    would_pay: Optional[str] = None
    nps: Optional[str] = None
    submitted_at: Optional[str] = None


@router.post("")
async def submit_feedback(request: FeedbackRequest):
    try:
        supabase.table("feedback").insert({
            "email": request.email,
            "name": request.name,
            "linkedin_url": request.linkedin_url,
            "from_role": request.from_role,
            "target_role": request.target_role,
            "pain_points": request.pain_points,
            "biggest_struggle": request.biggest_struggle,
            "would_pay": request.would_pay,
            "nps": request.nps,
        }).execute()

        # Notify team via email
        try:
            from app.services.notifications.email import _notify_team_feedback
            await _notify_team_feedback(request.email, request.name, request.would_pay)
        except Exception:
            pass  # Don't fail if notification fails

        logger.info(f"Feedback received from {request.email} — would_pay: {request.would_pay}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        return {"success": True}  # Always return 200 — don't lose signal


@router.get("/summary")
async def get_feedback_summary():
    """Internal endpoint — summary stats for team."""
    resp = supabase.table("feedback").select("would_pay, target_role, nps").execute()
    data = resp.data or []

    would_pay_yes = len([d for d in data if d.get("would_pay") == "yes_definitely"])
    would_pay_maybe = len([d for d in data if d.get("would_pay") == "yes_maybe"])
    avg_nps = sum(int(d["nps"]) for d in data if d.get("nps")) / max(len([d for d in data if d.get("nps")]), 1)

    return {
        "total_responses": len(data),
        "would_pay_definitely": would_pay_yes,
        "would_pay_maybe": would_pay_maybe,
        "conversion_intent": round((would_pay_yes + would_pay_maybe) / max(len(data), 1) * 100, 1),
        "avg_pain_score": round(avg_nps, 1),
        "target_role_breakdown": {
            role: len([d for d in data if d.get("target_role") == role])
            for role in set(d.get("target_role", "") for d in data if d.get("target_role"))
        },
    }
