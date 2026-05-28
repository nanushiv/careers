"""
Role Fit Analyzer — semantic similarity + LLM fit assessment.
"""
import logging
from typing import Optional
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.ai.cost_governor import cost_governor
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)


class RoleFitResult:
    def __init__(self):
        self.role_fit_score: float = 0.0
        self.semantic_score: float = 0.0
        self.fit_rationale: str = ""
        self.application_recommendation: str = "apply_with_improvements"
        self.dimension_scores: dict = {}
        self.strongest_alignment: list = []
        self.critical_gaps: list = []
        self.positioning_advice: str = ""
        self.model_used: Optional[str] = None
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.cache_hit: bool = False

    def to_dict(self) -> dict:
        return self.__dict__


class RoleFitAnalyzer:

    async def analyze(
        self,
        resume_text: str,
        jd_text: str,
        resume_sections: Optional[dict] = None,
        resume_id: Optional[str] = None,
        jd_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_plan: str = "free",
    ) -> RoleFitResult:

        result = RoleFitResult()

        # Cache check
        if resume_id and jd_id:
            cached = await cache_manager.get_analysis(resume_id, jd_id, "role_fit")
            if cached:
                result.cache_hit = True
                result.__dict__.update(cached)
                return result

        # Semantic similarity via embeddings
        try:
            resume_emb = await llm_client.embed(resume_text[:6000])
            jd_emb = await llm_client.embed(jd_text[:6000])
            sim = cosine_similarity(
                np.array(resume_emb).reshape(1, -1),
                np.array(jd_emb).reshape(1, -1),
            )[0][0]
            result.semantic_score = round(float(sim) * 100, 1)
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            result.semantic_score = 50.0

        # LLM enrichment
        llm_decision = await cost_governor.can_use_llm(
            user_id or "anon", user_plan, "role_fit"
        )

        if llm_decision["allowed"] and llm_decision["mode"] in ("full", "degraded"):
            model = cost_governor.select_model(user_plan, "role_fit", llm_decision["mode"])
            prompt = get_prompt("role_fit").format(
                resume_sections=str(resume_sections or resume_text[:2000]),
                role_details=jd_text[:2000],
                semantic_score=result.semantic_score,
            )
            try:
                llm_resp = await llm_client.complete(prompt, model=model)
                data = llm_resp.as_json()

                result.role_fit_score = data.get("role_fit_score", result.semantic_score)
                result.fit_rationale = data.get("fit_rationale", "")
                result.application_recommendation = data.get("application_recommendation", "apply_with_improvements")
                result.dimension_scores = data.get("dimension_scores", {})
                result.strongest_alignment = data.get("strongest_alignment", [])
                result.critical_gaps = data.get("critical_gaps", [])
                result.positioning_advice = data.get("positioning_advice", "")
                result.model_used = model
                result.tokens_used = llm_resp.tokens
                result.cost_usd = llm_resp.cost_usd

                if user_id:
                    await cost_governor.record_spend(user_id, llm_resp.cost_usd)

            except Exception as e:
                logger.error(f"Role fit LLM failed: {e}")
                result.role_fit_score = result.semantic_score
        else:
            result.role_fit_score = result.semantic_score

        if resume_id and jd_id:
            await cache_manager.set_analysis(resume_id, jd_id, "role_fit", result.to_dict())

        return result


role_fit_analyzer = RoleFitAnalyzer()
