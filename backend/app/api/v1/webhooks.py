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


# ── Razorpay Webhooks ─────────────────────────────────────────────────────────

@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    """
    Handle Razorpay subscription lifecycle events.
    Verified via HMAC SHA256 using RAZORPAY_WEBHOOK_SECRET.
    """
    import hmac as _hmac
    import hashlib

    body = await request.body()

    # Signature verification
    if settings.RAZORPAY_WEBHOOK_SECRET:
        received_sig = request.headers.get("x-razorpay-signature", "")
        expected_sig = _hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not _hmac.compare_digest(expected_sig, received_sig):
            logger.warning("Invalid Razorpay webhook signature")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = await request.json()
    event = payload.get("event", "")
    entity = payload.get("payload", {})

    logger.info(f"Razorpay webhook: {event}")

    if event == "subscription.activated":
        # First successful payment — activate Pro
        sub = entity.get("subscription", {}).get("entity", {})
        await _rzp_handle_activated(sub)

    elif event == "subscription.charged":
        # Recurring payment succeeded — keep Pro active, update period
        sub = entity.get("subscription", {}).get("entity", {})
        await _rzp_handle_charged(sub)

    elif event in ("subscription.cancelled", "subscription.completed", "subscription.expired"):
        # Subscription ended — downgrade to Free
        sub = entity.get("subscription", {}).get("entity", {})
        await _rzp_handle_ended(sub, event)

    elif event == "payment.failed":
        payment = entity.get("payment", {}).get("entity", {})
        logger.warning(
            f"Razorpay payment failed: id={payment.get('id')} "
            f"sub={payment.get('subscription_id')} reason={payment.get('error_description')}"
        )
        # Razorpay retries automatically — only downgrade on subscription.cancelled/expired

    return {"received": True}


async def _rzp_handle_activated(sub: dict):
    """subscription.activated — first payment succeeded, activate Pro."""
    from app.api.v1.billing import _activate_pro
    from datetime import datetime, timezone

    sub_id = sub.get("id", "")
    notes = sub.get("notes", {})
    user_id = notes.get("user_id", "")

    if not user_id:
        logger.error(f"No user_id in Razorpay subscription notes: {sub_id}")
        return

    charge_at = sub.get("charge_at")
    period_end = datetime.fromtimestamp(charge_at, tz=timezone.utc).isoformat() if charge_at else None

    _activate_pro(user_id, sub_id)
    if period_end:
        supabase.table("users").update({"plan_expires_at": period_end}).eq("id", user_id).execute()
        supabase.table("subscriptions").update({
            "current_period_end": period_end,
        }).eq("stripe_sub_id", sub_id).execute()

    logger.info(f"Pro activated via Razorpay webhook for user {user_id}, sub {sub_id}")


async def _rzp_handle_charged(sub: dict):
    """subscription.charged — recurring payment succeeded, refresh period dates."""
    from datetime import datetime, timezone

    sub_id = sub.get("id", "")
    charge_at = sub.get("charge_at")
    period_end = datetime.fromtimestamp(charge_at, tz=timezone.utc).isoformat() if charge_at else None

    supabase.table("subscriptions").update({
        "status": "active",
        "current_period_end": period_end,
    }).eq("stripe_sub_id", sub_id).execute()

    sub_record = supabase.table("subscriptions").select("user_id").eq(
        "stripe_sub_id", sub_id
    ).limit(1).execute()
    if sub_record.data and period_end:
        supabase.table("users").update({
            "plan_expires_at": period_end
        }).eq("id", sub_record.data[0]["user_id"]).execute()

    logger.info(f"Subscription renewed: {sub_id}")


async def _rzp_handle_ended(sub: dict, event: str):
    """subscription.cancelled / completed / expired — downgrade to Free."""
    from app.api.v1.billing import _deactivate_pro

    sub_id = sub.get("id", "")
    _deactivate_pro(sub_id)
    logger.info(f"Subscription ended ({event}): {sub_id}")
