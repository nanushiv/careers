"""
Users API — profile CRUD, onboarding, plan info.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.core.security import get_current_user
from app.core.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter()


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    current_title: Optional[str] = None
    target_roles: Optional[List[str]] = None
    years_experience: Optional[int] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    onboarding_completed: Optional[bool] = None
    onboarding_step: Optional[int] = None


def api_response(data=None, error=None):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


def _get_user_row(clerk_id: str, select: str = "id"):
    """Return first matching user row or None (never throws on empty)."""
    resp = supabase.table("users").select(select).eq("clerk_id", clerk_id).execute()
    return resp.data[0] if resp.data else None


def _create_user(clerk_id: str, email: str):
    """Insert a new user row and return it."""
    resp = supabase.table("users").insert({
        "clerk_id": clerk_id,
        "email": email,
    }).execute()
    return resp.data[0] if resp.data else None


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user = _get_user_row(current_user["clerk_id"], "*, usage_quotas(*), subscriptions(*)")
    if not user:
        user = _create_user(current_user["clerk_id"], current_user.get("email", ""))
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")
    return api_response(data=user)


@router.patch("/me")
async def update_me(
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    user = _get_user_row(current_user["clerk_id"])
    if not user:
        user = _create_user(current_user["clerk_id"], current_user.get("email", ""))
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

    update_data = request.model_dump(exclude_none=True)
    resp = supabase.table("users").update(update_data).eq("id", user["id"]).execute()
    return api_response(data=resp.data[0] if resp.data else {})


@router.get("/me/quota")
async def get_quota(current_user: dict = Depends(get_current_user)):
    user = _get_user_row(current_user["clerk_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    quota = supabase.table("usage_quotas").select("*").eq("user_id", user["id"]).execute()
    return api_response(data=quota.data[0] if quota.data else {})
