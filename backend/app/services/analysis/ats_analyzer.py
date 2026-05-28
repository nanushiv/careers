"""
ATS Analyzer — Rule Engine → Embeddings → LLM (lazy AI pattern).
"""
import logging
from typing import Optional
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.ai.rule_engine import rule_engine, RuleEngineResult
from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.ai.cost_governor import cost_governor
from app.core.cache import cache_manager, make_cache_key

logger = logging.getLogger(__name__)


class ATSAnalysisResult:
    def __init__(self):
        self.overall_score: float = 0.0
        self.keyword_score: float = 0.0
        self.format_score: float = 0.0
        self.experience_score: float = 0.0
        self.semantic_score: float = 0.0

        self.gaps: list = []
        self.strengths: list = []
        self.improvements: list = []
        self.keyword_analysis: dict = {}
        self.narrative_coherence: dict = {}
        self.quick_fixes: list = []
        self.ats_red_flags: list = []

        self.model_used: Optional[str] = None
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.cache_hit: bool = False
        self.processing_mode: str = "full"

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "keyword_score": self.keyword_score,
            "format_score": self.format_score,
            "experience_score": self.experience_score,
            "semantic_score": self.semantic_score,
            "gaps": self.gaps,
            "strengths": self.strengths,
            "improvements": self.improvements,
            "keyword_analysis": self.keyword_analysis,
            "narrative_coherence": self.narrative_coherence,
            "quick_fixes": self.quick_fixes,
            "ats_red_flags": self.ats_red_flags,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "cache_hit": self.cache_hit,
            "processing_mode": self.processing_mode,
        }


class ATSAnalyzer:

    async def analyze(
        self,
        resume_text: str,
        jd_text: Optional[str] = None,
        resume_id: Optional[str] = None,
        jd_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_plan: str = "free",
    ) -> ATSAnalysisResult:

        result = ATSAnalysisResult()

        # ── Cache check ────────────────────────────────────────────────────────
        if resume_id:
            cached = await cache_manager.get_analysis(
                resume_id, jd_id or "no_jd", "ats"
            )
            if cached:
                logger.info(f"ATS cache hit | resume={resume_id}")
                result.cache_hit = True
                self._load_from_dict(result, cached)
                return result

        # ── Layer 1: Rule Engine ───────────────────────────────────────────────
        rule_result = rule_engine.analyze(resume_text, jd_text)
        result.keyword_score = rule_result.keyword_score
        result.format_score = rule_result.format_score
        result.ats_red_flags = rule_result.ats_red_flags

        result.keyword_analysis = {
            "required_found": rule_result.required_keywords_found,
            "required_missing": rule_result.required_keywords_missing,
            "preferred_found": rule_result.preferred_keywords_found,
            "preferred_missing": rule_result.preferred_keywords_missing,
            "density": rule_result.keyword_density,
        }

        # Build gaps from missing keywords
        for kw in rule_result.required_keywords_missing[:5]:
            result.gaps.append({
                "type": "keyword",
                "severity": "high",
                "keyword": kw,
                "description": f"'{kw}' appears in the job description but not your resume",
                "fix": f"Add '{kw}' naturally in your experience descriptions",
            })

        # ── Layer 2: Semantic Similarity (embeddings) ──────────────────────────
        if jd_text and resume_text:
            try:
                resume_emb = await llm_client.embed(resume_text[:4000])
                jd_emb = await llm_client.embed(jd_text[:4000])
                similarity = cosine_similarity(
                    np.array(resume_emb).reshape(1, -1),
                    np.array(jd_emb).reshape(1, -1),
                )[0][0]
                result.semantic_score = round(float(similarity) * 100, 1)
            except Exception as e:
                logger.warning(f"Embedding similarity failed: {e}")
                result.semantic_score = 50.0

        # ── Layer 3: LLM enrichment (conditional) ─────────────────────────────
        llm_decision = await cost_governor.can_use_llm(
            user_id or "anon", user_plan, "ats"
        )
        result.processing_mode = llm_decision["mode"]

        should_call_llm = (
            llm_decision["allowed"]
            and llm_decision["mode"] == "full"
            and rule_result.confidence < 0.8
            and jd_text
        )

        if should_call_llm:
            model = cost_governor.select_model(user_plan, "ats", llm_decision["mode"])
            prompt = get_prompt("ats").format(
                resume_text=resume_text[:3000],
                jd_text=jd_text[:2000],
                rule_engine_output=str({
                    "keyword_score": rule_result.keyword_score,
                    "missing_keywords": rule_result.required_keywords_missing[:10],
                    "format_issues": rule_result.format_issues[:5],
                }),
            )
            try:
                llm_resp = await llm_client.complete(prompt, model=model)
                ai_data = llm_resp.as_json()

                # Merge AI insights
                result.gaps.extend([
                    {**gap, "source": "ai"}
                    for gap in ai_data.get("semantic_gaps", [])
                ])
                result.narrative_coherence = ai_data.get("narrative_coherence", {})
                result.quick_fixes = ai_data.get("quick_fixes", [])
                result.experience_score = ai_data.get("experience_relevance", {}).get("score", 50)

                # Adjust score with AI feedback
                result.keyword_score = max(0, min(100,
                    result.keyword_score + ai_data.get("ats_score_adjustment", 0)
                ))

                result.model_used = model
                result.tokens_used = llm_resp.tokens
                result.cost_usd = llm_resp.cost_usd

                # Record spend
                if user_id:
                    await cost_governor.record_spend(user_id, llm_resp.cost_usd)

            except Exception as e:
                logger.error(f"LLM ATS enrichment failed: {e}")

        # ── Compute overall score ─────────────────────────────────────────────
        weights = {
            "keyword": 0.40,
            "semantic": 0.25,
            "format": 0.20,
            "experience": 0.15,
        }
        result.overall_score = round(
            result.keyword_score * weights["keyword"]
            + result.semantic_score * weights["semantic"]
            + result.format_score * weights["format"]
            + (result.experience_score or 60) * weights["experience"],
            1,
        )

        # Build improvements from gaps
        result.improvements = [
            {
                "priority": gap["severity"],
                "action": gap.get("fix", gap.get("description", "")),
                "impact": "high" if gap["severity"] in ["critical", "high"] else "medium",
                "effort": "minutes",
            }
            for gap in result.gaps[:5]
        ]

        # ── Cache result ───────────────────────────────────────────────────────
        if resume_id:
            await cache_manager.set_analysis(
                resume_id, jd_id or "no_jd", "ats", result.to_dict()
            )

        return result

    def _load_from_dict(self, result: ATSAnalysisResult, data: dict):
        for key, value in data.items():
            if hasattr(result, key):
                setattr(result, key, value)


ats_analyzer = ATSAnalyzer()
