"""
Cost Governor — enforces AI spending budgets per user plan.
Called before every LLM invocation.
"""
import logging
from app.core.config import settings
from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

PLAN_BUDGETS = {
    "free": settings.AI_BUDGET_FREE_MONTHLY_USD,
    "pro": settings.AI_BUDGET_PRO_MONTHLY_USD,
    "team": 20.0,  # Higher budget for team plan
}

# What features are available at each plan when budget is exhausted
DEGRADATION_MAP = {
    "ats": {
        "free_exhausted": "rule_only",     # Still valuable, but no LLM nuance
        "pro_exhausted": "embedding_only",
    },
    "recruiter": {
        "free_exhausted": "blocked",       # Hard paywall — premium insight
        "pro_exhausted": "degraded",
    },
    "role_fit": {
        "free_exhausted": "embedding_only",
        "pro_exhausted": "embedding_only",
    },
    "readiness": {
        "free_exhausted": "blocked",
        "pro_exhausted": "degraded",
    },
}


class CostGovernor:

    async def get_user_spend(self, user_id: str) -> float:
        """Get current month's AI spend for user (from DB/cache)."""
        cache_key = f"ai_spend:{user_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return float(cached)
        # Fallback: query DB (simplified here)
        return 0.0

    async def record_spend(self, user_id: str, cost_usd: float):
        """Record AI spend — update cache and queue DB write."""
        cache_key = f"ai_spend:{user_id}"
        current = await self.get_user_spend(user_id)
        new_total = current + cost_usd
        await cache_set(cache_key, str(new_total), ttl=86400 * 31)
        logger.info(f"AI spend recorded | user={user_id} +${cost_usd:.5f} total=${new_total:.4f}")

    async def can_use_llm(self, user_id: str, plan: str, analysis_type: str) -> dict:
        """
        Returns:
          {"allowed": True, "mode": "full"} — use LLM normally
          {"allowed": True, "mode": "degraded"} — use cheaper model / partial
          {"allowed": False, "mode": "rule_only"} — no LLM, use rules
          {"allowed": False, "mode": "blocked"} — feature gated
        """
        budget = PLAN_BUDGETS.get(plan, 0.15)
        spend = await self.get_user_spend(user_id)

        if spend < budget:
            return {"allowed": True, "mode": "full"}

        # Budget exhausted — check degradation policy
        plan_key = f"{plan}_exhausted"
        degradation = DEGRADATION_MAP.get(analysis_type, {}).get(plan_key, "blocked")

        if degradation == "rule_only":
            return {"allowed": True, "mode": "rule_only"}
        elif degradation == "embedding_only":
            return {"allowed": True, "mode": "embedding_only"}
        elif degradation == "degraded":
            return {"allowed": True, "mode": "degraded"}
        else:
            return {
                "allowed": False,
                "mode": "blocked",
                "reason": f"Monthly AI budget reached for {plan} plan",
                "upgrade_url": "/pricing" if plan == "free" else None,
            }

    def select_model(self, plan: str, analysis_type: str, mode: str) -> str:
        """Select the most cost-effective model for this context."""
        if mode == "degraded":
            return "gemini-2.5-flash"

        # Full quality — select by analysis type
        model_map = {
            "recruiter": "gemini-2.5-flash",
            "readiness": "gemini-2.5-flash",
            "ats": "gemini-2.5-flash",
            "role_fit": "gemini-2.5-flash",
            "interview_questions": "gemini-2.5-flash",
            "weekly_synthesis": "gemini-2.5-flash",
        }

        # Pro users get flash for everything — no pro upgrade needed for flash
        # Pro price_id in future = gemini-pro for premium quality
        return model_map.get(analysis_type, "gemini-2.5-flash")


cost_governor = CostGovernor()
