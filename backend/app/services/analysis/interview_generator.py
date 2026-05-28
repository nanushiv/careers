"""
Interview Question Generator — tailored prep questions for a specific role + stage.
"""
import logging
from typing import Optional

from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.ai.cost_governor import cost_governor
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)


class InterviewQuestionsResult:
    def __init__(self):
        self.questions: list = []
        self.key_themes: list = []
        self.weak_points_to_prepare: list = []
        self.one_question_to_nail: str = ""
        self.model_used: Optional[str] = None
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.cache_hit: bool = False

    def to_dict(self) -> dict:
        return self.__dict__


class InterviewGenerator:

    async def generate(
        self,
        resume_text: str,
        role_title: str,
        company_name: str,
        interview_stage: str = "general",
        resume_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_plan: str = "free",
    ) -> InterviewQuestionsResult:

        result = InterviewQuestionsResult()

        cache_key = f"{resume_id}_{role_title}_{interview_stage}" if resume_id else None
        if cache_key:
            cached = await cache_manager.get_analysis(resume_id, cache_key, "interview_questions")
            if cached:
                result.cache_hit = True
                result.__dict__.update(cached)
                return result

        llm_decision = await cost_governor.can_use_llm(
            user_id or "anon", user_plan, "ats"
        )
        if not llm_decision["allowed"]:
            return result

        model = cost_governor.select_model(user_plan, "interview_questions", llm_decision["mode"])

        # Build resume summary for prompt
        resume_summary = resume_text[:2500]

        prompt = get_prompt("interview_questions").format(
            resume_summary=resume_summary,
            role_title=role_title,
            company_name=company_name,
            interview_stage=interview_stage,
        )

        try:
            llm_resp = await llm_client.complete(prompt, model=model, max_tokens=2500)
            data = llm_resp.as_json()

            result.questions = data.get("questions", [])
            result.key_themes = data.get("key_themes_to_prepare", [])
            result.weak_points_to_prepare = data.get("resume_weak_points_likely_probed", [])
            result.one_question_to_nail = data.get("one_question_to_nail", "")
            result.model_used = model
            result.tokens_used = llm_resp.tokens
            result.cost_usd = llm_resp.cost_usd

            if user_id:
                await cost_governor.record_spend(user_id, llm_resp.cost_usd)

        except Exception as e:
            logger.error(f"Interview generation failed: {e}")

        if cache_key:
            await cache_manager.set_analysis(resume_id, cache_key, "interview_questions", result.to_dict())

        return result


interview_generator = InterviewGenerator()
