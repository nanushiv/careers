"""
Dashboard API — aggregates all user data for dashboard views.
Cached aggressively since it's called on every page load.
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import logging

from app.core.security import get_current_user
from app.core.database import supabase
from app.core.cache import cache_get, cache_set, make_cache_key

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user(current_user: dict) -> dict:
    resp = supabase.table("users").select("*").eq(
        "clerk_id", current_user["clerk_id"]
    ).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    return resp.data[0]


def api_response(data=None, error=None):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


@router.get("")
async def get_main_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Main dashboard aggregate: career health, insights, weekly snapshot, pipeline mini.
    Cached for 5 minutes.
    """
    user = get_user(current_user)
    cache_key = make_cache_key("dashboard", user["id"])
    cached = await cache_get(cache_key)
    if cached:
        return api_response(data=cached)

    # ── Applications summary ──────────────────────────────────────────────────
    try:
        apps = supabase.table("applications").select(
            "id, stage, outcome, application_source, role_category, applied_date, company_name, role_title"
        ).eq("user_id", user["id"]).is_("deleted_at", "null").execute()
        all_apps = apps.data or []
    except Exception as e:
        logger.error(f"Dashboard apps query failed: {e}")
        all_apps = []

    active_apps = [a for a in all_apps if a["stage"] not in ("rejected", "ghosted", "withdrawn")]

    stage_counts = {}
    for app in active_apps:
        stage = app["stage"]
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # ── Callback rate (apps with stage beyond "applied") ─────────────────────
    callbacks = [a for a in all_apps if a["stage"] not in ("applied", "rejected", "ghosted")]
    callback_rate = round(len(callbacks) / len(all_apps) * 100, 1) if all_apps else 0

    # ── This week's apps ──────────────────────────────────────────────────────
    week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
    week_apps = [a for a in all_apps if a.get("applied_date", "") >= week_ago]

    # ── Upcoming follow-ups ───────────────────────────────────────────────────
    today = datetime.now().date().isoformat()
    try:
        follow_ups = supabase.table("follow_ups").select(
            "id, due_date, status, application_id"
        ).eq("user_id", user["id"]).eq("status", "pending").gte(
            "due_date", today
        ).order("due_date").limit(5).execute()
        follow_ups_data = follow_ups.data or []
    except Exception as e:
        logger.error(f"Dashboard follow_ups query failed: {e}")
        follow_ups_data = []

    # ── Recent insights ───────────────────────────────────────────────────────
    try:
        insights = supabase.table("ai_insights").select("*").eq(
            "user_id", user["id"]
        ).eq("is_dismissed", False).order(
            "created_at", desc=True
        ).limit(3).execute()
        insights_data = insights.data or []
    except Exception as e:
        logger.error(f"Dashboard insights query failed: {e}")
        insights_data = []

    # ── Resume performance ────────────────────────────────────────────────────
    try:
        resumes = supabase.table("resumes").select(
            "id, version_label, callback_rate, applications_used, ats_score_avg, is_primary"
        ).eq("user_id", user["id"]).is_("deleted_at", "null").execute()
        resumes_data = resumes.data or []
    except Exception as e:
        logger.error(f"Dashboard resumes query failed: {e}")
        resumes_data = []

    # ── Career health score (weighted composite) ──────────────────────────────
    career_health = _compute_career_health(
        total_apps=len(all_apps),
        callback_rate=callback_rate,
        active_pipeline=len(active_apps),
        has_interviews=any(a["stage"] in ("technical", "case_study", "final") for a in all_apps),
        has_offers=any(a["stage"] == "offer" for a in all_apps),
        ghost_rate=len([a for a in all_apps if a["stage"] == "ghosted"]) / max(len(all_apps), 1) * 100,
    )

    dashboard_data = {
        "career_health_score": career_health,
        "user": {
            "full_name": user.get("full_name"),
            "plan": user.get("plan", "free"),
            "target_roles": user.get("target_roles", []),
        },
        "pipeline_summary": {
            "total": len(all_apps),
            "active": len(active_apps),
            "this_week": len(week_apps),
            "callback_rate": callback_rate,
            "stage_distribution": stage_counts,
        },
        "follow_ups": follow_ups_data,
        "insights": insights_data,
        "resumes": resumes_data,
        "recent_applications": all_apps[:5],
    }

    await cache_set(cache_key, dashboard_data, ttl=90)  # 90s cache
    return api_response(data=dashboard_data)


@router.get("/debug-tables")
async def debug_tables(current_user: dict = Depends(get_current_user)):
    """Temporary: shows which Supabase tables are reachable for this user."""
    user = get_user(current_user)
    results = {}
    for table in ["applications", "follow_ups", "ai_insights", "resumes", "usage_quotas"]:
        try:
            resp = supabase.table(table).select("id").eq("user_id", user["id"]).limit(1).execute()
            results[table] = f"ok ({len(resp.data or [])} rows sample)"
        except Exception as e:
            results[table] = f"ERROR: {e}"
    return {"user_id": user["id"], "tables": results}


@router.get("/pipeline")
async def get_pipeline_dashboard(current_user: dict = Depends(get_current_user)):
    """Full pipeline view with kanban data."""
    user = get_user(current_user)

    apps = supabase.table("applications").select("*").eq(
        "user_id", user["id"]
    ).is_("deleted_at", "null").order("applied_date", desc=True).execute()

    all_apps = apps.data or []

    # Group by stage for kanban
    kanban = {}
    stages = ["applied", "screening", "phone_screen", "technical", "case_study", "final", "offer"]
    for stage in stages:
        kanban[stage] = [a for a in all_apps if a["stage"] == stage]

    # Funnel conversion rates
    funnel = _compute_funnel(all_apps)

    # Source performance
    source_stats = _compute_source_stats(all_apps)

    return api_response(data={
        "kanban": kanban,
        "funnel": funnel,
        "source_performance": source_stats,
        "ghosted": [a for a in all_apps if a["stage"] == "ghosted"],
        "rejected": [a for a in all_apps if a["stage"] == "rejected"],
    })


@router.get("/analytics")
async def get_analytics_dashboard(
    period_weeks: int = 12,
    current_user: dict = Depends(get_current_user),
):
    """Analytics time-series data."""
    user = get_user(current_user)

    snapshots = supabase.table("user_analytics").select("*").eq(
        "user_id", user["id"]
    ).order("week_start", desc=True).limit(period_weeks).execute()

    # All-time stats
    apps = supabase.table("applications").select(
        "application_source, role_category, stage, outcome, applied_date"
    ).eq("user_id", user["id"]).is_("deleted_at", "null").execute()

    all_apps = apps.data or []

    resume_perf = supabase.table("resumes").select(
        "id, version_label, callback_rate, applications_used, ats_score_avg"
    ).eq("user_id", user["id"]).is_("deleted_at", "null").execute()

    # Enrich ats_score_avg from resume_analyses if not set on resumes table
    resumes_list = resume_perf.data or []
    for r in resumes_list:
        if not r.get("ats_score_avg"):
            ats_rows = supabase.table("resume_analyses").select("overall_score").eq(
                "resume_id", r["id"]
            ).eq("analysis_type", "ats").order("created_at", desc=True).limit(1).execute()
            if ats_rows.data:
                r["ats_score_avg"] = ats_rows.data[0]["overall_score"]

    return api_response(data={
        "weekly_snapshots": list(reversed(snapshots.data or [])),
        "resume_performance": resumes_list,
        "source_breakdown": _compute_source_stats(all_apps),
        "category_breakdown": _compute_category_stats(all_apps),
        "stage_drop_off": _compute_funnel(all_apps),
    })


@router.get("/recruiter")
async def get_recruiter_dashboard(current_user: dict = Depends(get_current_user)):
    """Recruiter intelligence hub — aggregated perception insights."""
    user = get_user(current_user)

    # Latest recruiter analysis
    latest_recruiter = supabase.table("resume_analyses").select("*").eq(
        "user_id", user["id"]
    ).eq("analysis_type", "recruiter").order("created_at", desc=True).limit(1).execute()

    # Score history
    score_history = supabase.table("resume_analyses").select(
        "overall_score, created_at, resume_id"
    ).eq("user_id", user["id"]).eq("analysis_type", "recruiter").order(
        "created_at"
    ).execute()

    return api_response(data={
        "latest_analysis": latest_recruiter.data[0] if latest_recruiter.data else None,
        "score_history": score_history.data or [],
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_career_health(
    total_apps: int,
    callback_rate: float,
    active_pipeline: int,
    has_interviews: bool,
    has_offers: bool,
    ghost_rate: float,
) -> float:
    score = 40.0  # Base

    # Application volume (max 15 pts)
    if total_apps >= 20:
        score += 15
    elif total_apps >= 10:
        score += 10
    elif total_apps >= 5:
        score += 5

    # Callback rate (max 25 pts)
    if callback_rate >= 20:
        score += 25
    elif callback_rate >= 10:
        score += 15
    elif callback_rate >= 5:
        score += 8

    # Active pipeline (max 10 pts)
    if active_pipeline >= 5:
        score += 10
    elif active_pipeline >= 2:
        score += 5

    # Interview presence (10 pts)
    if has_interviews:
        score += 10

    # Offer presence (10 pts)
    if has_offers:
        score += 10

    # Ghost rate penalty (max -10 pts)
    if ghost_rate > 50:
        score -= 10
    elif ghost_rate > 30:
        score -= 5

    return round(min(100, max(0, score)), 1)


def _compute_funnel(apps: list) -> list:
    stages = ["applied", "screening", "phone_screen", "technical", "case_study", "final", "offer"]
    total = len(apps)
    if total == 0:
        return []

    funnel = []
    for i, stage in enumerate(stages):
        at_or_past_stage = len([
            a for a in apps
            if (stages.index(a["stage"]) >= i if a["stage"] in stages else False)
        ])
        prev = funnel[-1]["count"] if funnel else total
        funnel.append({
            "stage": stage,
            "count": at_or_past_stage,
            "conversion_rate": round(at_or_past_stage / max(prev, 1) * 100, 1),
        })
    return funnel


def _compute_source_stats(apps: list) -> dict:
    stats = {}
    for app in apps:
        src = app.get("application_source", "unknown")
        if src not in stats:
            stats[src] = {"total": 0, "callbacks": 0}
        stats[src]["total"] += 1
        if app.get("stage") not in ("applied", "rejected", "ghosted"):
            stats[src]["callbacks"] += 1

    for src in stats:
        t = stats[src]["total"]
        c = stats[src]["callbacks"]
        stats[src]["callback_rate"] = round(c / t * 100, 1) if t > 0 else 0

    return stats


def _compute_category_stats(apps: list) -> dict:
    stats = {}
    for app in apps:
        cat = app.get("role_category", "Other") or "Other"
        stats[cat] = stats.get(cat, 0) + 1
    return stats
