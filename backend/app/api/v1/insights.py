"""
Insights API — retrieve, dismiss, and act on AI insights.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from app.core.security import get_current_user
from app.core.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("")
async def list_insights(
    priority: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)
    query = supabase.table("ai_insights").select("*").eq(
        "user_id", user_id
    ).eq("is_dismissed", False).order("created_at", desc=True).limit(limit)

    if priority:
        query = query.eq("priority", priority)

    resp = query.execute()
    return api_response(data=resp.data)


@router.get("/{insight_id}")
async def get_insight(insight_id: str, current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    resp = supabase.table("ai_insights").select("*").eq(
        "id", insight_id
    ).eq("user_id", user_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Insight not found")
    return api_response(data=resp.data)


@router.post("/{insight_id}/dismiss")
async def dismiss_insight(insight_id: str, current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    resp = supabase.table("ai_insights").update(
        {"is_dismissed": True}
    ).eq("id", insight_id).eq("user_id", user_id).execute()
    return api_response(data=resp.data[0] if resp.data else {})


@router.post("/{insight_id}/acted-on")
async def mark_acted_on(insight_id: str, current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    resp = supabase.table("ai_insights").update(
        {"is_acted_on": True}
    ).eq("id", insight_id).eq("user_id", user_id).execute()
    return api_response(data=resp.data[0] if resp.data else {})
