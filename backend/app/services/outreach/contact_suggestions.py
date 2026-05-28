"""
Contact Suggestion Service — AI-generated outreach targets.
Suggests real archetypes of people to reach out to based on resume + target roles.
No external API needed — pure Gemini inference.
"""
import logging
from app.ai.llm_client import llm_client

logger = logging.getLogger(__name__)

CONTACT_SUGGESTION_PROMPT = """
You are a senior career strategist helping a job seeker identify the best people to cold-email.

CANDIDATE:
- Name: {user_name}
- Current title: {current_title}
- Targeting: {target_roles}
- Resume summary (first 2000 chars): {resume_text}

Generate 6 specific, strategic outreach targets. Each should be a real type of person who:
1. Is in a role that can hire, refer, or meaningfully advise on {target_roles} positions
2. Works at a company well-known for strong {target_roles_short} teams
3. Would be receptive to a thoughtful, well-crafted cold email

Return a JSON array — nothing else:
[
  {{
    "title": "specific job title (e.g. 'Director of Product, Growth')",
    "company": "real company name (well-known, active hiring)",
    "why": "1–2 sentences on why THIS person is worth reaching — weave in something from the candidate's background, not generic advice",
    "goal": "informational_interview|referral_request|job_inquiry|networking",
    "linkedin_keywords": "natural keywords to find them (e.g. 'Head of Product Stripe')"
  }}
]

Rules:
- Use real, recognizable companies — mix FAANG, unicorns (Stripe, Figma, Notion, Linear), Series B/C startups
- Vary goal: 2 informational_interview, 2 referral_request, 1 job_inquiry, 1 networking
- "why" must reference the candidate's actual background — no boilerplate
- Vary seniority: not all VPs; include ICs, managers, leads
- All 6 must feel actionable and strategic, not random
"""


async def get_contact_suggestions(
    resume_text: str,
    target_roles: list[str],
    user_name: str = "",
    current_title: str = "",
) -> list[dict]:
    """Generate AI contact archetypes for outreach targeting."""
    try:
        target_roles_str = ", ".join(target_roles[:3]) if target_roles else "Product Manager"
        target_roles_short = target_roles[0] if target_roles else "PM"

        prompt = CONTACT_SUGGESTION_PROMPT.format(
            user_name=user_name or "the candidate",
            current_title=current_title or "professional",
            target_roles=target_roles_str,
            target_roles_short=target_roles_short,
            resume_text=resume_text[:2000] if resume_text else "No resume provided yet.",
        )

        llm_resp = await llm_client.complete(
            prompt, model="gemini-2.5-flash-lite", max_tokens=1500, temperature=0.7
        )
        data = llm_resp.as_json()

        if not isinstance(data, list):
            logger.warning("Contact suggestion returned non-list response")
            return []

        return [
            {
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "why": item.get("why", ""),
                "goal": item.get("goal", "informational_interview"),
                "linkedin_keywords": item.get("linkedin_keywords", ""),
            }
            for item in data[:6]
            if item.get("title") and item.get("company")
        ]

    except Exception as e:
        logger.error(f"Contact suggestion generation failed: {e}")
        return []
