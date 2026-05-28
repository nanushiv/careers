"""
Webhooks — Clerk user lifecycle + Stripe subscription events.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
import logging

from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Clerk Webhooks ────────────────────────────────────────────────────────────

@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: Optional[str] = Header(None),
    svix_timestamp: Optional[str] = Header(None),
    svix_signature: Optional[str] = Header(None),
):
    """Handle Clerk user lifecycle events."""
    body = await request.body()

    # Verify Svix signature
    if settings.CLERK_WEBHOOK_SECRET:
        if not _verify_svix(body, svix_id, svix_timestamp, svix_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"Clerk webhook: {event_type}")

    if event_type == "user.created":
        await _handle_user_created(data)
    elif event_type == "user.updated":
        await _handle_user_updated(data)
    elif event_type == "user.deleted":
        await _handle_user_deleted(data)

    return {"received": True}


async def _handle_user_created(data: dict):
    clerk_id = data.get("id")
    email = data.get("email_addresses", [{}])[0].get("email_address", "")
    first = data.get("first_name", "")
    last = data.get("last_name", "")
    avatar = data.get("image_url", "")

    supabase.table("users").upsert({
        "clerk_id": clerk_id,
        "email": email,
        "full_name": f"{first} {last}".strip(),
        "avatar_url": avatar,
    }).execute()
    logger.info(f"User created: {clerk_id}")


async def _handle_user_updated(data: dict):
    clerk_id = data.get("id")
    email = data.get("email_addresses", [{}])[0].get("email_address", "")
    first = data.get("first_name", "")
    last = data.get("last_name", "")

    supabase.table("users").update({
        "email": email,
        "full_name": f"{first} {last}".strip(),
    }).eq("clerk_id", clerk_id).execute()


async def _handle_user_deleted(data: dict):
    clerk_id = data.get("id")
    supabase.table("users").update({
        "deleted_at": "NOW()"
    }).eq("clerk_id", clerk_id).execute()
    logger.info(f"User soft-deleted: {clerk_id}")


def _verify_svix(
    body: bytes,
    svix_id: Optional[str],
    svix_timestamp: Optional[str],
    svix_signature: Optional[str],
) -> bool:
    if not all([svix_id, svix_timestamp, svix_signature]):
        return False
    signed = f"{svix_id}.{svix_timestamp}.{body.decode()}"
    secret = settings.CLERK_WEBHOOK_SECRET.replace("whsec_", "")
    import base64
    key = base64.b64decode(secret)
    expected = base64.b64encode(
        hmac.new(key, signed.encode(), hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(f"v1,{expected}", svix_signature or "")


# ── Stripe Webhooks ───────────────────────────────────────────────────────────

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
):
    """Handle Stripe subscription lifecycle events."""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type = event["type"]
    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "customer.subscription.created":
        await _handle_sub_created(event["data"]["object"])
    elif event_type == "customer.subscription.updated":
        await _handle_sub_updated(event["data"]["object"])
    elif event_type == "customer.subscription.deleted":
        await _handle_sub_cancelled(event["data"]["object"])

    return {"received": True}


async def _handle_sub_created(sub: dict):
    customer_id = sub["customer"]
    plan = "pro"  # Determine from price ID
    user_metadata = sub.get("metadata", {})
    user_id = user_metadata.get("user_id")

    if user_id:
        supabase.table("users").update({"plan": plan}).eq("id", user_id).execute()
        supabase.table("usage_quotas").update({
            "analyses_limit": 9999,
            "applications_limit": 9999,
        }).eq("user_id", user_id).execute()
        supabase.table("subscriptions").upsert({
            "user_id": user_id,
            "plan": plan,
            "status": "active",
            "stripe_sub_id": sub["id"],
        }).execute()
        logger.info(f"Pro subscription created for user: {user_id}")


async def _handle_sub_updated(sub: dict):
    stripe_sub_id = sub["id"]
    status = sub["status"]

    supabase.table("subscriptions").update({
        "status": status,
        "cancel_at_period_end": sub.get("cancel_at_period_end", False),
    }).eq("stripe_sub_id", stripe_sub_id).execute()


async def _handle_sub_cancelled(sub: dict):
    stripe_sub_id = sub["id"]
    sub_record = supabase.table("subscriptions").select("user_id").eq(
        "stripe_sub_id", stripe_sub_id
    ).limit(1).execute()

    if sub_record.data:
        user_id = sub_record.data[0]["user_id"]
        supabase.table("users").update({"plan": "free"}).eq("id", user_id).execute()
        supabase.table("usage_quotas").update({
            "analyses_limit": 5,
            "applications_limit": 10,
        }).eq("user_id", user_id).execute()
        supabase.table("subscriptions").update({
            "status": "cancelled"
        }).eq("stripe_sub_id", stripe_sub_id).execute()
        logger.info(f"Subscription cancelled, user reverted to free: {user_id}")
