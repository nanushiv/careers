"""
Analyses API — trigger AI analyses and retrieve results.
Analysis jobs are async: trigger returns job_id, poll for completion.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
import logging

from app.core.security import get_current_user
from app.core.database import get_db, supabase
from app.core.config import is_admin
from app.services.analysis.ats_analyzer import ats_analyzer
from app.services.analysis.recruiter_analyzer import recruiter_analyzer
from app.services.analysis.readiness_scorer import readiness_scorer
from app.services.analysis.role_fit_analyzer import role_fit_analyzer
from app.services.analysis.interview_generator import interview_generator

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    resume_id: str
    jd_id: Optional[str] = None
    jd_text: Optional[str] = None  # paste JD text directly — auto-saved to DB
    analysis_types: List[str] = ["ats", "recruiter", "role_fit", "readiness"]


class AnalysisJobResponse(BaseModel):
    job_id: str
    status: str
    estimated_seconds: int


class AnalysisResponse(BaseModel):
    id: str
    analysis_type: str
    overall_score: Optional[float]
    status: str
    data: dict


def api_response(data=None, error=None, status_code=200):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
async def trigger_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Trigger one or more analyses. Returns a job_id immediately.
    Frontend subscribes to Supabase Realtime for status updates.
    """
    # Fetch user from DB
    user_resp = supabase.table("users").select("*").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_resp.data[0]

    # Check quota
    quota_resp = supabase.table("usage_quotas").select("*").eq(
        "user_id", user["id"]
    ).execute()
    quota = quota_resp.data[0] if quota_resp.data else None

    if quota and quota["analyses_used"] >= quota["analyses_limit"] and user["plan"] == "free" and not is_admin(user.get("email", "")):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": f"You've used your {quota['analyses_limit']} free analyses. Upgrade to Pro for unlimited AI analysis.",
                "analyses_used": quota["analyses_used"],
                "analyses_limit": quota["analyses_limit"],
                "upgrade_url": "/pricing",
            },
        )

    # Fetch resume text
    resume_resp = supabase.table("resumes").select("*").eq(
        "id", request.resume_id
    ).eq("user_id", user["id"]).execute()

    if not resume_resp.data or not resume_resp.data[0].get("raw_text"):
        raise HTTPException(status_code=404, detail="Resume not found or not yet parsed")

    resume = resume_resp.data[0]

    # Resolve JD text
    jd_text = None
    jd_id = request.jd_id
    if request.jd_text and request.jd_text.strip():
        if len(request.jd_text) > 50_000:
            raise HTTPException(status_code=400, detail="Job description too long. Max 50,000 characters.")
        # Save pasted JD text to DB and get an ID
        jd_saved = supabase.table("job_descriptions").insert({
            "user_id": user["id"],
            "raw_text": request.jd_text.strip(),
            "parse_status": "pending",
        }).execute()
        if jd_saved.data:
            jd_id = jd_saved.data[0]["id"]
        jd_text = request.jd_text.strip()
    elif jd_id:
        jd_resp = supabase.table("job_descriptions").select("*").eq(
            "id", jd_id
        ).eq("user_id", user["id"]).execute()
        if jd_resp.data:
            jd_text = jd_resp.data[0].get("raw_text", "")

    # Create job record
    job_id = str(uuid.uuid4())

    # Update job status in Supabase (Realtime will notify frontend)
    supabase.table("analysis_jobs").upsert({
        "id": job_id,
        "user_id": user["id"],
        "resume_id": request.resume_id,
        "jd_id": jd_id,
        "analysis_types": request.analysis_types,
        "status": "queued",
    }).execute()

    # Run analysis in background
    background_tasks.add_task(
        run_analyses_background,
        job_id=job_id,
        user=user,
        resume=resume,
        jd_text=jd_text,
        jd_id=request.jd_id,
        analysis_types=request.analysis_types,
    )

    return api_response(data={
        "job_id": job_id,
        "status": "queued",
        "estimated_seconds": len(request.analysis_types) * 8,
    })


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll job status — lets frontend detect failures immediately."""
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    job = supabase.table("analysis_jobs").select("id, status, error, results").eq(
        "id", job_id
    ).eq("user_id", user_resp.data[0]["id"]).limit(1).execute()

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return api_response(data=job.data[0])


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a completed analysis by ID."""
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    analysis_resp = supabase.table("resume_analyses").select("*").eq(
        "id", analysis_id
    ).eq("user_id", user_resp.data[0]["id"]).execute()

    if not analysis_resp.data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return api_response(data=analysis_resp.data[0])


@router.get("")
async def list_analyses(
    resume_id: Optional[str] = None,
    analysis_type: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List analyses for the current user."""
    user_resp = supabase.table("users").select("id").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()

    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        query = supabase.table("resume_analyses").select("*").eq(
            "user_id", user_resp.data[0]["id"]
        ).order("created_at", desc=True).limit(limit)

        if resume_id:
            query = query.eq("resume_id", resume_id)
        if analysis_type:
            query = query.eq("analysis_type", analysis_type)

        resp = query.execute()
        return api_response(data=resp.data)
    except Exception as e:
        logger.error(f"list_analyses query failed: {e}")
        return api_response(data=[])


# ── Interview Questions ────────────────────────────────────────────────────────

class InterviewQuestionsRequest(BaseModel):
    resume_id: str
    role_title: str
    company_name: str = ""
    interview_stage: str = "general"  # general | phone | technical | final


@router.post("/interview-questions")
async def generate_interview_questions(
    request: InterviewQuestionsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate tailored interview questions for a resume + role. Available to all plans."""
    user_resp = supabase.table("users").select("id, plan, email").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_resp.data[0]

    resume_resp = supabase.table("resumes").select("id, raw_text").eq(
        "id", request.resume_id
    ).eq("user_id", user["id"]).execute()
    if not resume_resp.data or not resume_resp.data[0].get("raw_text"):
        raise HTTPException(status_code=404, detail="Resume not found or not yet parsed")
    resume = resume_resp.data[0]

    result = await interview_generator.generate(
        resume_text=resume["raw_text"],
        role_title=request.role_title,
        company_name=request.company_name,
        interview_stage=request.interview_stage,
        resume_id=resume["id"],
        user_id=user["id"],
        user_plan=user.get("plan", "free"),
    )

    # Persist to resume_analyses so results are cached and retrievable
    record = {
        "user_id": user["id"],
        "resume_id": resume["id"],
        "analysis_type": "interview_questions",
        "interview_questions": {
            "questions": result.questions,
            "key_themes": result.key_themes,
            "weak_points_to_prepare": result.weak_points_to_prepare,
            "one_question_to_nail": result.one_question_to_nail,
            "role_title": request.role_title,
            "company_name": request.company_name,
            "interview_stage": request.interview_stage,
        },
        "model_used": result.model_used,
        "tokens_used": result.tokens_used,
        "cost_usd": result.cost_usd,
        "cache_hit": result.cache_hit,
    }
    stored = supabase.table("resume_analyses").insert(record).execute()
    row_id = stored.data[0]["id"] if stored.data else None

    return api_response(data={
        "id": row_id,
        "cache_hit": result.cache_hit,
        **record["interview_questions"],
    })


# ── Background Job ────────────────────────────────────────────────────────────

async def run_analyses_background(
    job_id: str,
    user: dict,
    resume: dict,
    jd_text: Optional[str],
    jd_id: Optional[str],
    analysis_types: List[str],
):
    """Run all requested analyses and store results."""
    try:
        supabase.table("analysis_jobs").update({"status": "processing"}).eq(
            "id", job_id
        ).execute()

        resume_text = resume["raw_text"]
        jd_structured = None
        if jd_id:
            jd_rows = supabase.table("job_descriptions").select("*").eq("id", jd_id).execute()
            jd_structured = jd_rows.data[0] if jd_rows.data else None

        results = []

        for analysis_type in analysis_types:
            try:
                analysis_record = None

                if analysis_type == "ats":
                    result = await ats_analyzer.analyze(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        resume_id=resume["id"],
                        jd_id=jd_id,
                        user_id=user["id"],
                        user_plan=user.get("plan", "free"),
                    )
                    d = result.to_dict()
                    analysis_record = {
                        "user_id": user["id"],
                        "resume_id": resume["id"],
                        "jd_id": jd_id,
                        "analysis_type": "ats",
                        "overall_score": result.overall_score,
                        "keyword_score": d.get("keyword_score"),
                        "format_score": d.get("format_score"),
                        "experience_score": d.get("experience_score"),
                        "gaps": d.get("gaps", []),
                        "strengths": d.get("strengths", []),
                        "improvements": d.get("improvements", []),
                        "keyword_analysis": d.get("keyword_analysis", {}),
                        "improvement_roadmap": d.get("quick_fixes", []),
                        "model_used": d.get("model_used"),
                        "tokens_used": d.get("tokens_used", 0),
                        "cost_usd": d.get("cost_usd", 0),
                        "cache_hit": d.get("cache_hit", False),
                    }

                elif analysis_type == "recruiter":
                    role_category = jd_structured.get("role_category", "PM") if jd_structured else "PM"
                    role_level = jd_structured.get("role_level", "senior") if jd_structured else "senior"
                    result = await recruiter_analyzer.analyze(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        role_category=role_category,
                        role_level=role_level,
                        resume_id=resume["id"],
                        jd_id=jd_id,
                        user_id=user["id"],
                        user_plan=user.get("plan", "free"),
                    )
                    d = result.to_dict()
                    analysis_record = {
                        "user_id": user["id"],
                        "resume_id": resume["id"],
                        "jd_id": jd_id,
                        "analysis_type": "recruiter",
                        "overall_score": result.perception_score,
                        # Nest all recruiter data under recruiter_signals (what the frontend reads)
                        "recruiter_signals": {
                            "perception_score": d.get("perception_score"),
                            "first_impression": d.get("first_impression"),
                            "likelihood_to_shortlist": d.get("likelihood_to_shortlist"),
                            "standout_positives": d.get("standout_positives", []),
                            "immediate_concerns": d.get("immediate_concerns", []),
                            "positioning_gaps": d.get("positioning_gaps", []),
                            "narrative_story": d.get("narrative_story"),
                            "vs_typical_applicant": d.get("vs_typical_applicant"),
                            "recommended_changes": d.get("recommended_changes", []),
                            "interview_likelihood_rationale": d.get("interview_likelihood_rationale"),
                        },
                        "model_used": d.get("model_used"),
                        "tokens_used": d.get("tokens_used", 0),
                        "cost_usd": d.get("cost_usd", 0),
                        "cache_hit": d.get("cache_hit", False),
                    }

                elif analysis_type == "readiness":
                    result = await readiness_scorer.score(
                        resume_text=resume_text,
                        resume_id=resume["id"],
                        user_id=user["id"],
                        user_plan=user.get("plan", "free"),
                    )
                    d = result.to_dict()
                    analysis_record = {
                        "user_id": user["id"],
                        "resume_id": resume["id"],
                        "jd_id": jd_id,
                        "analysis_type": "readiness",
                        "overall_score": result.overall_readiness_score,
                        # Nest all readiness data under readiness_breakdown (what the frontend reads)
                        "readiness_breakdown": {
                            "role_detected": d.get("role_detected", "PM"),
                            "role_label": d.get("role_label", "Product Manager"),
                            "overall_readiness_score": d.get("overall_readiness_score"),
                            "readiness_level": d.get("readiness_level"),
                            "dimensions": d.get("dimensions", {}),
                            "positioning_narrative": d.get("positioning_narrative"),
                            "critical_missing_experiences": d.get("critical_missing_experiences", []),
                            "quick_wins_30_days": d.get("quick_wins_30_days", []),
                            "estimated_readiness_timeline": d.get("estimated_readiness_timeline"),
                        },
                        "model_used": d.get("model_used"),
                        "tokens_used": d.get("tokens_used", 0),
                        "cost_usd": d.get("cost_usd", 0),
                        "cache_hit": d.get("cache_hit", False),
                    }

                elif analysis_type == "role_fit":
                    if not jd_text:
                        logger.warning("role_fit skipped: no JD text provided")
                        continue
                    result = await role_fit_analyzer.analyze(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        resume_sections=resume.get("structured_data"),
                        resume_id=resume["id"],
                        jd_id=jd_id,
                        user_id=user["id"],
                        user_plan=user.get("plan", "free"),
                    )
                    d = result.to_dict()
                    analysis_record = {
                        "user_id": user["id"],
                        "resume_id": resume["id"],
                        "jd_id": jd_id,
                        "analysis_type": "role_fit",
                        "overall_score": result.role_fit_score,
                        "role_fit_analysis": {
                            "role_fit_score": d.get("role_fit_score"),
                            "semantic_score": d.get("semantic_score"),
                            "fit_rationale": d.get("fit_rationale"),
                            "application_recommendation": d.get("application_recommendation"),
                            "dimension_scores": d.get("dimension_scores", {}),
                            "strongest_alignment": d.get("strongest_alignment", []),
                            "critical_gaps": d.get("critical_gaps", []),
                            "positioning_advice": d.get("positioning_advice"),
                        },
                        "model_used": d.get("model_used"),
                        "tokens_used": d.get("tokens_used", 0),
                        "cost_usd": d.get("cost_usd", 0),
                        "cache_hit": d.get("cache_hit", False),
                    }

                if analysis_record is None:
                    continue

                stored = supabase.table("resume_analyses").insert(analysis_record).execute()
                results.append({"type": analysis_type, "id": stored.data[0]["id"]})

                # Fix #5: update ats_score_avg on the resume after a successful ATS analysis
                if analysis_type == "ats":
                    try:
                        supabase.table("resumes").update({
                            "ats_score_avg": round(result.overall_score)
                        }).eq("id", resume["id"]).execute()
                    except Exception as score_err:
                        logger.warning(f"Failed to update ats_score_avg: {score_err}")

            except Exception as e:
                logger.error(f"Analysis {analysis_type} failed: {e}")
                results.append({"type": analysis_type, "error": str(e)})

        # Update quota
        quota_resp = supabase.table("usage_quotas").select("analyses_used").eq("user_id", user["id"]).execute()
        current_used = quota_resp.data[0]["analyses_used"] if quota_resp.data else 0
        supabase.table("usage_quotas").update({
            "analyses_used": current_used + 1
        }).eq("user_id", user["id"]).execute()

        # Fix #4: if every analysis failed, mark job as failed so frontend stops polling
        successful = [r for r in results if "id" in r]
        if not successful:
            errors = [r.get("error", "") for r in results if "error" in r]
            is_quota = any("GEMINI_QUOTA_EXCEEDED" in e for e in errors)
            fail_msg = (
                "AI quota exhausted for today. Resets at ~12:30 PM IST. Please try again tomorrow."
                if is_quota else
                "All analyses failed. Please try again in a minute."
            )
            supabase.table("analysis_jobs").update({
                "status": "failed",
                "error": fail_msg,
                "results": results,
            }).eq("id", job_id).execute()
        else:
            # Mark job complete
            supabase.table("analysis_jobs").update({
                "status": "completed",
                "results": results,
            }).eq("id", job_id).execute()

    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {e}")
        supabase.table("analysis_jobs").update({
            "status": "failed",
            "error": str(e),
        }).eq("id", job_id).execute()
