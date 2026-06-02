"""
Insight Engine — detects patterns across user data and generates AI-powered insights.
Called by the weekly worker or on-demand.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.core.database import supabase

logger = logging.getLogger(__name__)


class InsightEngine:

    async def generate_weekly_insights(self, user_id: str) -> list[dict]:
        """Generate strategic insights for a user based on their data."""
        # Gather all data
        user_resp = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
        if not user_resp.data:
            return []
        user = user_resp.data[0]

        apps = supabase.table("applications").select("*").eq(
            "user_id", user_id
        ).is_("deleted_at", "null").order("created_at", desc=True).execute().data or []

        recent_insights = supabase.table("ai_insights").select("title").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(10).execute().data or []

        insights = []

        # ── Rule-based pattern detection (always free) ─────────────────────
        rule_insights = self._detect_rule_patterns(user, apps)
        insights.extend(rule_insights)

        # ── LLM synthesis (weekly, throttled) ─────────────────────────────
        if len(apps) >= 5:
            llm_insights = await self._generate_llm_insights(user, apps, recent_insights)
            insights.extend(llm_insights)

        # Store new insights
        stored = []
        for insight in insights[:3]:  # Max 3 per run
            existing_titles = [r["title"] for r in recent_insights]
            if insight["title"] not in existing_titles:
                resp = supabase.table("ai_insights").insert({
                    "user_id": user_id,
                    **insight,
                }).execute()
                if resp.data:
                    stored.append(resp.data[0])

        return stored

    def _detect_rule_patterns(self, user: dict, apps: list) -> list[dict]:
        insights = []
        now = datetime.now()

        if not apps:
            return []

        total = len(apps)
        callbacks = [a for a in apps if a["stage"] not in ("applied", "rejected", "ghosted")]
        callback_rate = len(callbacks) / total * 100 if total > 0 else 0

        ghosted = [a for a in apps if a["stage"] == "ghosted"]
        ghost_rate = len(ghosted) / total * 100 if total > 0 else 0

        # ── Callback rate alarm ────────────────────────────────────────────
        if total >= 10 and callback_rate < 5:
            insights.append({
                "insight_type": "callback_pattern",
                "priority": "critical",
                "title": f"Critical: Only {callback_rate:.0f}% callback rate after {total} applications",
                "summary": "Your resume or positioning may be significantly mismatched to the roles you're targeting.",
                "detail": "A callback rate below 5% after 10+ applications almost always signals a fundamental positioning issue — not a numbers problem. The fix is strategic, not volume.",
                "action": "Run a fresh ATS + Recruiter Perception analysis against your last 3 job descriptions.",
                "impact": "Even fixing one positioning mismatch can double your callback rate.",
            })

        # ── Ghosting pattern ───────────────────────────────────────────────
        if ghost_rate > 40 and total >= 8:
            insights.append({
                "insight_type": "ghosting_pattern",
                "priority": "high",
                "title": f"{ghost_rate:.0f}% of your applications ended in silence",
                "summary": "High ghosting rates often indicate applying too late in posting cycles or to over-subscribed roles.",
                "detail": "When over 40% of applications receive zero response, it's usually timing (old postings) or volume competition (LinkedIn Easy Apply roles with 500+ applicants).",
                "action": "Switch to direct company applications or referrals for the next 10 applications.",
                "impact": "Referral-backed applications have 4x higher response rates.",
            })

        # ── Source performance ─────────────────────────────────────────────
        source_stats: dict = {}
        for app in apps:
            src = app.get("application_source", "unknown")
            if src not in source_stats:
                source_stats[src] = {"total": 0, "callbacks": 0}
            source_stats[src]["total"] += 1
            if app["stage"] not in ("applied", "rejected", "ghosted"):
                source_stats[src]["callbacks"] += 1

        best_src = max(source_stats, key=lambda k: source_stats[k]["callbacks"] / max(source_stats[k]["total"], 1))
        worst_src = min(source_stats, key=lambda k: source_stats[k]["callbacks"] / max(source_stats[k]["total"], 1))

        if (source_stats[best_src]["callbacks"] / max(source_stats[best_src]["total"], 1) > 0.2
                and source_stats[worst_src]["total"] >= 5
                and source_stats[worst_src]["callbacks"] == 0):
            insights.append({
                "insight_type": "source_performance",
                "priority": "high",
                "title": f"{best_src.replace('_', ' ').title()} is your best source — double down",
                "summary": f"{best_src} is generating callbacks while {worst_src.replace('_', ' ')} has 0 responses from {source_stats[worst_src]['total']} attempts.",
                "detail": f"Not all application sources perform equally for your profile. {best_src} is clearly resonating.",
                "action": f"Shift 80% of new applications to {best_src}. Cut {worst_src.replace('_', ' ')} for now.",
                "impact": "Concentrating effort on what works multiplies efficiency.",
            })

        # ── Application velocity ───────────────────────────────────────────
        week_ago = now - timedelta(days=7)
        recent_apps = [
            a for a in apps
            if a.get("applied_date") and
            datetime.fromisoformat(a["applied_date"].replace("Z", "")) > week_ago
        ]
        if len(recent_apps) == 0 and total > 0:
            insights.append({
                "insight_type": "application_velocity",
                "priority": "medium",
                "title": "No new applications this week",
                "summary": "Consistent weekly application volume is one of the strongest predictors of search success.",
                "detail": "Job searches stall when application momentum drops. Even 3-5 quality applications per week keeps the pipeline healthy.",
                "action": "Set a target of 5 tailored applications this week. Quality over quantity.",
                "impact": "Consistent velocity keeps your pipeline alive and generates more data for AI optimization.",
            })

        # ── Offer detected ─────────────────────────────────────────────────
        offers = [a for a in apps if a["stage"] == "offer"]
        if offers:
            co = offers[0]["company_name"]
            insights.append({
                "insight_type": "stage_drop_off",
                "priority": "critical",
                "title": f"You have an offer from {co} — time to negotiate",
                "summary": f"Congratulations! {co} extended an offer. First offers are rarely the best offers.",
                "detail": "Studies show 85% of hiring managers expect candidates to negotiate. The average first offer is 5-10% below the top of the band. Use competing offers or interviews in your pipeline as leverage.",
                "action": "Research salary bands on Levels.fyi / Glassdoor. Counter at least 10% above the offer. Mention your other active processes.",
                "impact": "A successful negotiation typically adds $10K–$30K in year-1 comp.",
            })

        # ── Final-round momentum ───────────────────────────────────────────
        finals = [a for a in apps if a["stage"] == "final"]
        if finals:
            companies = ", ".join(a["company_name"] for a in finals[:3])
            insights.append({
                "insight_type": "stage_drop_off",
                "priority": "high",
                "title": f"Final-round interviews active at {companies}",
                "summary": f"You're in the final stage at {len(finals)} company{'s' if len(finals) > 1 else ''}. This is where preparation pays off.",
                "detail": "Final rounds typically include cross-functional interviews, executive conversations, and case presentations. Candidates who research the company's recent priorities and current business context score significantly higher.",
                "action": "Review the company's latest earnings, product launches, and press releases. Prepare 2-3 strategic questions for each interviewer.",
                "impact": "Thorough final-round prep increases offer rates by ~40%.",
            })

        # ── Dream role in pipeline ─────────────────────────────────────────
        dream_active = [a for a in apps if a.get("is_dream_role") and a["stage"] not in ("rejected", "ghosted", "withdrawn")]
        if dream_active and not finals:  # Don't double-show if already in finals insight
            co_list = ", ".join(a["company_name"] for a in dream_active[:2])
            insights.append({
                "insight_type": "role_fit_trend",
                "priority": "high",
                "title": f"Dream role active at {co_list} — prioritize these",
                "summary": f"You have {len(dream_active)} dream-role application(s) still in play. Treat these as top priority.",
                "detail": "Dream roles rarely open twice. Follow up proactively, tailor your materials specifically to these companies, and keep your pipeline active to maintain negotiating leverage.",
                "action": f"Send a thoughtful follow-up to {dream_active[0]['company_name']} referencing something specific about their mission or recent news.",
                "impact": "Proactive follow-ups increase response rates by 30% and signal strong interest.",
            })

        # ── Strong callback rate positive signal ───────────────────────────
        if total >= 5 and callback_rate >= 40:
            insights.append({
                "insight_type": "callback_pattern",
                "priority": "medium",
                "title": f"Strong {callback_rate:.0f}% callback rate — your resume is working",
                "summary": "Your current resume and targeting strategy is resonating. Now focus on converting interviews to offers.",
                "detail": "A callback rate above 40% puts you in the top quartile of job seekers. The bottleneck has shifted from resume quality to interview performance.",
                "action": "Run through STAR-format answers for your top 5 behavioral questions. Consider a mock interview session.",
                "impact": "Interview preparation is now the highest-leverage activity in your search.",
            })

        return insights

    async def _generate_llm_insights(self, user: dict, apps: list, recent_insights: list) -> list[dict]:
        """Call LLM for strategic synthesis insights."""
        try:
            total = len(apps)
            callbacks = len([a for a in apps if a["stage"] not in ("applied", "rejected", "ghosted")])
            week_apps = len([a for a in apps if a.get("applied_date", "") >= (datetime.now() - timedelta(days=7)).date().isoformat()])

            prompt = get_prompt("weekly_synthesis").format(
                current_role=user.get("current_title", "Unknown"),
                target_roles=", ".join(user.get("target_roles", [])),
                weeks_searching=12,  # Would compute from created_at
                week_number="current",
                apps_this_week=week_apps,
                stage_changes=len([a for a in apps if a.get("last_stage_change_at")]),
                callback_rate=round(callbacks / max(total, 1) * 100, 1),
                cumulative_callback_rate=round(callbacks / max(total, 1) * 100, 1),
                interviews_scheduled=len([a for a in apps if a["stage"] in ("technical", "case_study", "final")]),
                pipeline_summary=f"{total} total, {callbacks} past screening",
                previous_insight_titles=", ".join([r["title"] for r in recent_insights[:5]]),
            )

            resp = await llm_client.complete(prompt, model="gemini-2.5-flash-lite", max_tokens=1500)
            data = resp.as_json()

            return [
                {
                    "insight_type": i.get("type", "strategic_pivot"),
                    "priority": i.get("priority", "medium"),
                    "title": i.get("title", ""),
                    "summary": i.get("summary", ""),
                    "detail": i.get("detail", ""),
                    "action": i.get("action", ""),
                    "impact": i.get("impact", ""),
                }
                for i in data.get("insights", [])
                if i.get("title")
            ]
        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            return []


insight_engine = InsightEngine()
