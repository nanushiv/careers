"""
Readiness Scorer — evaluates PM/AI readiness across 6 dimensions.
"""
import logging
from typing import Optional

from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.ai.cost_governor import cost_governor
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)


class ReadinessResult:
    def __init__(self):
        self.overall_readiness_score: float = 0.0
        self.readiness_level: str = "developing"
        self.dimensions: dict = {}
        self.positioning_narrative: str = ""
        self.critical_missing_experiences: list = []
        self.quick_wins_30_days: list = []
        self.estimated_readiness_timeline: str = "6 months"
        self.model_used: Optional[str] = None
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.cache_hit: bool = False
        self.blocked: bool = False

    def to_dict(self) -> dict:
        return self.__dict__


class ReadinessScorer:

    async def score(
        self,
        resume_text: str,
        target_role_type: str = "Product Manager",
        resume_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_plan: str = "free",
    ) -> ReadinessResult:

        result = ReadinessResult()

        # Cache check
        if resume_id:
            cached = await cache_manager.get_analysis(resume_id, target_role_type, "readiness")
            if cached:
                result.cache_hit = True
                result.__dict__.update(cached)
                return result

        # Check plan
        llm_decision = await cost_governor.can_use_llm(
            user_id or "anon", user_plan, "readiness"
        )
        if not llm_decision["allowed"]:
            result.blocked = True
            return result

        model = cost_governor.select_model(user_plan, "readiness", llm_decision["mode"])
        prompt = get_prompt("readiness").format(
            resume_text=resume_text[:4000],
            target_role_type=target_role_type,
        )

        try:
            llm_resp = await llm_client.complete(prompt, model=model, max_tokens=2500)
            data = llm_resp.as_json()

            result.overall_readiness_score = data.get("overall_readiness_score", 50)
            result.readiness_level = data.get("readiness_level", "developing")
            result.dimensions = data.get("dimensions", {})
            result.positioning_narrative = data.get("positioning_narrative", "")
            result.critical_missing_experiences = data.get("critical_missing_experiences", [])
            result.quick_wins_30_days = data.get("quick_wins_30_days", [])
            result.estimated_readiness_timeline = data.get("estimated_readiness_timeline", "6 months")
            result.model_used = model
            result.tokens_used = llm_resp.tokens
            result.cost_usd = llm_resp.cost_usd

            if user_id:
                await cost_governor.record_spend(user_id, llm_resp.cost_usd)

        except Exception as e:
            logger.error(f"Readiness scoring failed: {e}")
            raise

        if resume_id:
            await cache_manager.set_analysis(resume_id, target_role_type, "readiness", result.to_dict())

        return result


readiness_scorer = ReadinessScorer()
