"""
Analysis Worker — Celery tasks for async AI analysis jobs.
"""
import asyncio
import logging
from app.workers.runner import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def run_analysis_job(self, job_id: str, user_id: str, resume_id: str,
                     jd_id: str = None, analysis_types: list = None):
    """Run full analysis pipeline for a resume."""
    try:
        asyncio.run(_run_async(job_id, user_id, resume_id, jd_id, analysis_types or ["ats"]))
    except Exception as exc:
        logger.error(f"Analysis job {job_id} failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def _run_async(job_id, user_id, resume_id, jd_id, analysis_types):
    from app.core.database import supabase
    from app.services.analysis.ats_analyzer import ats_analyzer
    from app.services.analysis.recruiter_analyzer import recruiter_analyzer
    from app.services.analysis.role_fit_analyzer import role_fit_analyzer
    from app.services.analysis.readiness_scorer import readiness_scorer

    # Mark processing
    supabase.table("analysis_jobs").update({"status": "processing"}).eq("id", job_id).execute()

    resume = supabase.table("resumes").select("*").eq("id", resume_id).single().execute().data
    user = supabase.table("users").select("*").eq("id", user_id).single().execute().data

    if not resume or not resume.get("raw_text"):
        supabase.table("analysis_jobs").update({"status": "failed", "error": "Resume not parsed"}).eq("id", job_id).execute()
        return

    jd_text = None
    if jd_id:
        jd = supabase.table("job_descriptions").select("*").eq("id", jd_id).single().execute().data
        if jd:
            jd_text = jd.get("raw_text", "")

    resume_text = resume["raw_text"]
    plan = user.get("plan", "free") if user else "free"
    results = []

    for atype in analysis_types:
        try:
            if atype == "ats":
                r = await ats_analyzer.analyze(
                    resume_text=resume_text, jd_text=jd_text,
                    resume_id=resume_id, jd_id=jd_id,
                    user_id=user_id, user_plan=plan,
                )
                data = r.to_dict()
                score = r.overall_score
            elif atype == "recruiter":
                r = await recruiter_analyzer.analyze(
                    resume_text=resume_text, jd_text=jd_text,
                    resume_id=resume_id, jd_id=jd_id,
                    user_id=user_id, user_plan=plan,
                )
                data = r.to_dict()
                score = r.perception_score
            elif atype == "role_fit" and jd_text:
                r = await role_fit_analyzer.analyze(
                    resume_text=resume_text, jd_text=jd_text,
                    resume_id=resume_id, jd_id=jd_id,
                    user_id=user_id, user_plan=plan,
                )
                data = r.to_dict()
                score = r.role_fit_score
            elif atype == "readiness":
                r = await readiness_scorer.score(
                    resume_text=resume_text,
                    resume_id=resume_id, user_id=user_id, user_plan=plan,
                )
                data = r.to_dict()
                score = r.overall_readiness_score
            else:
                continue

            stored = supabase.table("resume_analyses").insert({
                "user_id": user_id,
                "resume_id": resume_id,
                "jd_id": jd_id,
                "analysis_type": atype,
                "overall_score": score,
                "gaps": data.get("gaps", []),
                "strengths": data.get("strengths", []),
                "improvements": data.get("improvements", []),
                "keyword_analysis": data.get("keyword_analysis", {}),
                "model_used": data.get("model_used"),
                "tokens_used": data.get("tokens_used", 0),
                "cost_usd": data.get("cost_usd", 0),
                "cache_hit": data.get("cache_hit", False),
            }).execute()
            results.append({"type": atype, "id": stored.data[0]["id"] if stored.data else None})

            # Update ats_score_avg on resumes table whenever an ATS analysis completes
            if atype == "ats":
                supabase.table("resumes").update({"ats_score_avg": score}).eq("id", resume_id).execute()

        except Exception as e:
            logger.error(f"Analysis {atype} failed: {e}")
            results.append({"type": atype, "error": str(e)})

    supabase.table("analysis_jobs").update({
        "status": "completed", "results": results
    }).eq("id", job_id).execute()
