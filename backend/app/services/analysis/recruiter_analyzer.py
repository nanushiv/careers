"""
Recruiter Perception Analyzer — simulates how a real recruiter sees this candidate.
This is the most premium and differentiated feature. Always uses LLM.
"""
import logging
from typing import Optional
from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.ai.cost_governor import cost_governor
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)


class RecruiterAnalysisResult:
    def __init__(self):
        self.perception_score: float = 0.0
        self.first_impression: str = ""
        self.likelihood_to_shortlist: str = "low"
        self.standout_positives: list = []
        self.immediate_concerns: list = []
        self.positioning_gaps: list = []
        self.narrative_story: str = ""
        self.vs_typical_applicant: str = ""
        self.recommended_changes: list = []
        self.interview_likelihood_rationale: str = ""

        self.model_used: Optional[str] = None
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.cache_hit: bool = False
        self.blocked: bool = False
        self.block_reason: str = ""

    def to_dict(self) -> dict:
        return self.__dict__


class RecruiterAnalyzer:

    async def analyze(
        self,
        resume_text: str,
        jd_text: Optional[str] = None,
        role_category: str = "PM",
        role_level: str = "senior",
        resume_id: Optional[str] = None,
        jd_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_plan: str = "free",
    ) -> RecruiterAnalysisResult:

        result = RecruiterAnalysisResult()

        # ── Cache check ────────────────────────────────────────────────────────
        if resume_id:
            cached = await cache_manager.get_analysis(
                resume_id, jd_id or "no_jd", "recruiter"
            )
            if cached:
                result.cache_hit = True
                result.__dict__.update(cached)
                return result

        # ── Cost/plan check — recruiter perception is premium ──────────────────
        llm_decision = await cost_governor.can_use_llm(
            user_id or "anon", user_plan, "recruiter"
        )

        if not llm_decision["allowed"]:
            result.blocked = True
            result.block_reason = llm_decision.get("reason", "Upgrade to Pro to unlock")
            return result

        # ── LLM Analysis ───────────────────────────────────────────────────────
        model = cost_governor.select_model(user_plan, "recruiter", llm_decision["mode"])

        jd_requirements = jd_text[:1500] if jd_text else "No specific JD provided — evaluate generally."

        prompt = get_prompt("recruiter").format(
            role_category=role_category,
            role_level=role_level,
            resume_text=resume_text[:3000],
            jd_requirements=jd_requirements,
        )

        try:
            llm_resp = await llm_client.complete(
                prompt, model=model, max_tokens=3000, temperature=0.4
            )
            data = llm_resp.as_json()

            result.perception_score = data.get("perception_score", 50)
            result.first_impression = data.get("first_impression", "")
            result.likelihood_to_shortlist = data.get("likelihood_to_shortlist", "medium")
            result.standout_positives = data.get("standout_positives", [])
            result.immediate_concerns = data.get("immediate_concerns", [])
            result.positioning_gaps = data.get("positioning_gaps", [])
            result.narrative_story = data.get("narrative_story", "")
            result.vs_typical_applicant = data.get("vs_typical_applicant", "")
            result.recommended_changes = data.get("recommended_resume_changes", [])
            result.interview_likelihood_rationale = data.get("interview_likelihood_rationale", "")

            result.model_used = model
            result.tokens_used = llm_resp.tokens
            result.cost_usd = llm_resp.cost_usd

            if user_id:
                await cost_governor.record_spend(user_id, llm_resp.cost_usd)

        except Exception as e:
            logger.error(f"Recruiter perception analysis failed: {e}")
            raise

        # ── Cache ──────────────────────────────────────────────────────────────
        if resume_id and not result.blocked:
            await cache_manager.set_analysis(
                resume_id, jd_id or "no_jd", "recruiter", result.to_dict()
            )

        return result


recruiter_analyzer = RecruiterAnalyzer()
