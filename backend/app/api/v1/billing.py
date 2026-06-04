"""
Billing API — Razorpay subscription management.
Supports UPI, credit/debit cards, net banking, and wallets (India + global).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
import hashlib
import hmac
import logging
from requests.auth import HTTPBasicAuth
import requests as _requests

from app.core.config import settings
from app.core.security import get_current_user
from app.core.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter()

RZP_BASE = "https://api.razorpay.com/v1"


def _rzp_auth():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    return HTTPBasicAuth(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)


def _rzp_post(path: str, data: dict) -> dict:
    resp = _requests.post(f"{RZP_BASE}{path}", json=data, auth=_rzp_auth(), timeout=10)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=f"Razorpay error: {resp.text}")
    return resp.json()


def _rzp_patch(path: str, data: dict) -> dict:
    resp = _requests.patch(f"{RZP_BASE}{path}", json=data, auth=_rzp_auth(), timeout=10)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=f"Razorpay error: {resp.text}")
    return resp.json()


# ── Country detection (kept for geo display) ──────────────────────────────────

async def _detect_country(request: Request) -> str:
    """Detect user country from IP. Returns 2-letter ISO code."""
    import httpx
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")
    if ip in ("127.0.0.1", "::1", "", "localhost"):
        return "IN"  # local dev — show INR pricing
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"https://ip-api.com/json/{ip}?fields=countryCode")
            return resp.json().get("countryCode", "IN")
    except Exception:
        return "IN"


@router.get("/country")
async def get_country(request: Request):
    """Detect user's country for frontend pricing display. No auth required."""
    country = await _detect_country(request)
    return {
        "success": True,
        "data": {
            "country": country,
            "is_india": country == "IN",
            "price_display": "₹999",   # Razorpay is INR-first
            "currency": "INR",
        }
    }


# ── Subscription creation ──────────────────────────────────────────────────────

@router.post("/create-subscription")
async def create_subscription(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Create a Razorpay subscription for the user.
    Returns subscription_id + key_id so frontend can open the checkout modal.
    """
    if not settings.RAZORPAY_PLAN_ID:
        raise HTTPException(status_code=500, detail="Payment plan not configured")

    user_resp = supabase.table("users").select("id, email, full_name, plan").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_resp.data[0]

    if user["plan"] == "pro":
        raise HTTPException(status_code=400, detail="Already on Pro plan")

    try:
        subscription = _rzp_post("/subscriptions", {
            "plan_id": settings.RAZORPAY_PLAN_ID,
            "total_count": 12,           # max 12 billing cycles (1 year); renews monthly
            "quantity": 1,
            "notes": {
                "user_id": user["id"],
                "email": user["email"],
            },
        })
        logger.info(f"Razorpay subscription created: {subscription['id']} for user {user['id']}")
        return {
            "success": True,
            "data": {
                "subscription_id": subscription["id"],
                "key_id": settings.RAZORPAY_KEY_ID,
                "name": "CareerOS Pro",
                "description": "Unlimited AI analyses, job matches, outreach drafts",
                "prefill": {
                    "name": user.get("full_name", ""),
                    "email": user["email"],
                },
            }
        }
    except Exception as e:
        logger.error(f"Razorpay subscription creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


# ── Payment verification (client-side confirmation) ────────────────────────────

@router.post("/verify-payment")
async def verify_payment(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Verify the payment signature returned by Razorpay modal.
    Called immediately after successful payment — gives instant UI feedback.
    The webhook is the authoritative source of truth for plan activation.
    """
    body = await request.json()
    payment_id = body.get("razorpay_payment_id", "")
    subscription_id = body.get("razorpay_subscription_id", "")
    signature = body.get("razorpay_signature", "")

    if not all([payment_id, subscription_id, signature]):
        raise HTTPException(status_code=400, detail="Missing payment verification fields")

    # Verify HMAC signature
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{payment_id}|{subscription_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning(f"Invalid Razorpay signature for payment {payment_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Upgrade user to pro immediately (webhook will also fire as backup)
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user_resp.data[0]["id"]
    _activate_pro(user_id, subscription_id, razorpay_payment_id=payment_id)
    logger.info(f"Payment verified and pro activated for user {user_id}")

    return {"success": True, "data": {"plan": "pro"}}


# ── Cancel subscription ────────────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel subscription at end of current billing period."""
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    sub_resp = supabase.table("subscriptions").select("stripe_sub_id").eq(
        "user_id", user_resp.data[0]["id"]
    ).eq("status", "active").limit(1).execute()

    if not sub_resp.data:
        raise HTTPException(status_code=404, detail="No active subscription found")

    razorpay_sub_id = sub_resp.data[0]["stripe_sub_id"]  # column reused for Razorpay sub ID

    try:
        # cancel_at_cycle_end=1 cancels at end of current billing cycle
        _rzp_patch(f"/subscriptions/{razorpay_sub_id}/cancel", {"cancel_at_cycle_end": 1})
        supabase.table("subscriptions").update({
            "cancel_at_period_end": True
        }).eq("stripe_sub_id", razorpay_sub_id).execute()
        logger.info(f"Subscription set to cancel at cycle end: {razorpay_sub_id}")
        return {"success": True, "data": {"message": "Subscription will cancel at end of billing period."}}
    except Exception as e:
        logger.error(f"Cancel subscription failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


# ── Shared helper ──────────────────────────────────────────────────────────────

def _activate_pro(user_id: str, razorpay_sub_id: str, razorpay_payment_id: str = ""):
    """Upgrade a user to Pro and record the subscription."""
    supabase.table("users").update({"plan": "pro"}).eq("id", user_id).execute()
    supabase.table("usage_quotas").update({
        "analyses_limit": 9999,
        "applications_limit": 9999,
    }).eq("user_id", user_id).execute()
    supabase.table("subscriptions").upsert({
        "user_id": user_id,
        "plan": "pro",
        "status": "active",
        "stripe_sub_id": razorpay_sub_id,   # column reused for Razorpay sub ID
    }).execute()


def _deactivate_pro(razorpay_sub_id: str):
    """Downgrade user to Free when subscription ends/cancels."""
    sub_record = supabase.table("subscriptions").select("user_id").eq(
        "stripe_sub_id", razorpay_sub_id
    ).limit(1).execute()
    if sub_record.data:
        user_id = sub_record.data[0]["user_id"]
        supabase.table("users").update({"plan": "free", "plan_expires_at": None}).eq("id", user_id).execute()
        supabase.table("usage_quotas").update({
            "analyses_limit": 5,
            "applications_limit": 10,
        }).eq("user_id", user_id).execute()
        supabase.table("subscriptions").update({
            "status": "cancelled"
        }).eq("stripe_sub_id", razorpay_sub_id).execute()
        logger.info(f"User {user_id} reverted to free plan")
