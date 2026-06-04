"""
Billing API — Stripe checkout session creation with geo-based pricing.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
import stripe
import httpx
import logging

from app.core.config import settings
from app.core.security import get_current_user
from app.core.database import supabase

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)
router = APIRouter()


async def _detect_country(request: Request) -> str:
    """Detect user country from IP. Returns 2-letter ISO code e.g. 'IN', 'US'."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")

    if ip in ("127.0.0.1", "::1", "", "localhost"):
        return "US"  # local dev — default to global

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"https://ip-api.com/json/{ip}?fields=countryCode")
            data = resp.json()
            return data.get("countryCode", "US")
    except Exception:
        return "US"


def _pick_price_id(country: str) -> str:
    """Return the correct Stripe price ID based on country."""
    if country == "IN" and settings.STRIPE_PRO_PRICE_ID_IN:
        return settings.STRIPE_PRO_PRICE_ID_IN
    return settings.STRIPE_PRO_PRICE_ID


@router.get("/country")
async def get_country(request: Request):
    """Detect user's country for frontend pricing display. No auth required."""
    country = await _detect_country(request)
    return {
        "success": True,
        "data": {
            "country": country,
            "is_india": country == "IN",
            "price_display": "₹999" if country == "IN" else "$29",
            "currency": "INR" if country == "IN" else "USD",
        }
    }


@router.post("/create-checkout")
async def create_checkout(request: Request, current_user: dict = Depends(get_current_user)):
    user_resp = supabase.table("users").select("id, email").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_resp.data[0]
    country = await _detect_country(request)
    price_id = _pick_price_id(country)

    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price not configured")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/dashboard?upgraded=true",
            cancel_url=f"{settings.FRONTEND_URL}/pricing",
            customer_email=user["email"],
            metadata={"user_id": user["id"]},
        )
        logger.info(f"Checkout created for user {user['id']} country={country} price={price_id}")
        return {"success": True, "data": {"url": session.url}}
    except Exception as e:
        logger.error(f"Stripe checkout failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel the user's Pro subscription at period end (not immediately)."""
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

    try:
        stripe.Subscription.modify(
            sub_resp.data[0]["stripe_sub_id"],
            cancel_at_period_end=True,
        )
        supabase.table("subscriptions").update({
            "cancel_at_period_end": True
        }).eq("stripe_sub_id", sub_resp.data[0]["stripe_sub_id"]).execute()
        logger.info(f"Subscription set to cancel at period end: {sub_resp.data[0]['stripe_sub_id']}")
        return {"success": True, "data": {"message": "Subscription will cancel at end of billing period."}}
    except Exception as e:
        logger.error(f"Cancel subscription failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/portal")
async def billing_portal(current_user: dict = Depends(get_current_user)):
    """Open Stripe customer portal to manage subscription."""
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    sub_resp = supabase.table("subscriptions").select("stripe_sub_id").eq(
        "user_id", user_resp.data[0]["id"]
    ).limit(1).execute()

    if not sub_resp.data:
        raise HTTPException(status_code=404, detail="No active subscription")

    try:
        sub = stripe.Subscription.retrieve(sub_resp.data[0]["stripe_sub_id"])
        portal = stripe.billing_portal.Session.create(
            customer=sub.customer,
            return_url=f"{settings.FRONTEND_URL}/settings",
        )
        return {"success": True, "data": {"url": portal.url}}
    except Exception as e:
        logger.error(f"Portal failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to open billing portal")
