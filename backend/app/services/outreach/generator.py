"""
Outreach Service — generates personalized cold emails to recruiters/hiring managers.
Premium feature. Never auto-sends — user always reviews + sends manually.
"""
import logging
from typing import Optional

from app.ai.llm_client import llm_client
from app.ai.cost_governor import cost_governor

logger = logging.getLogger(__name__)

GOAL_INSTRUCTIONS = {
    "informational_interview": """
GOAL: Request a 20-minute informational interview.
- Open with a genuine observation about their work/company (specific, not generic)
- Mention 1-2 of the sender's key strengths naturally in context — not as a brag, but to show you're worth their time
- Low-friction ask: "Would you have 20 minutes sometime in the next few weeks?"
- Tone: warm, curious, human — like a message from someone they'd enjoy talking to
""",
    "referral_request": """
GOAL: Ask for a referral for a specific role or team.
- Lead with a connection point or genuine admiration for their company
- Weave in 1-2 key strengths that make you a compelling candidate worth referring
- Be direct about wanting a referral — don't bury the ask
- Make it easy: "Would you be open to referring me, or passing my name to the hiring team?"
- Tone: confident but not presumptuous
""",
    "job_inquiry": """
GOAL: Direct inquiry about open roles or opportunities.
- Show you've done your homework on the company (mention something specific)
- Lead with your strongest 1-2 strengths that directly match what they need
- Ask about current or upcoming openings on a specific team
- Tone: direct, confident, professional — you're pitching yourself, own it
""",
    "networking": """
GOAL: Build a genuine professional connection.
- Find common ground (industry, mutual interests, their content/work)
- Mention your background briefly — include 1-2 strengths that make you interesting to talk to
- No transactional ask — just express genuine interest in connecting
- Tone: light, warm, conversational — the least "sales-y" of all goals
""",
    "thank_you_post_interview": """
GOAL: Post-interview thank you that reinforces your candidacy.
- Thank them specifically for something discussed in the interview (be specific)
- Reinforce 1-2 key strengths that came up or that you want to emphasize
- Reiterate your excitement for the role/team with specificity
- End with a warm, forward-looking close
- Tone: genuinely enthusiastic but not desperate
""",
}

OUTREACH_PROMPT = """
You are an expert career coach who writes cold outreach emails that actually get responses.
Your emails are known for feeling personal, direct, and impressive — never generic or ChatGPT-sounding.

SENDER:
- Name: {sender_name}
- Current role: {current_role}
- Transitioning to: {target_role}
- Key strengths from their resume: {key_strengths}

RECIPIENT:
- Name: {recipient_name}
- Title: {recipient_title}
- Company: {company_name}
- Additional context: {context}

{goal_instructions}

STRICT RULES:
- 100-130 words max (tight, punchy emails get more replies)
- NEVER start with "I hope", "My name is", or "I came across your profile"
- Naturally weave in at least ONE specific key strength from the sender's profile — make it feel organic, not like a resume bullet
- Reference something real and specific about {company_name} or {recipient_name}'s role — no generic flattery
- One clear ask at the end — make it frictionless and easy to say yes
- Write like a sharp, confident human, not an AI

Return JSON only:
{{
  "subject": "compelling subject line (under 8 words, spark curiosity)",
  "body": "full email body — paragraphs separated by \\n\\n",
  "tone": "warm|professional|direct",
  "word_count": number,
  "personalization_hooks": ["specific detail about recipient used", "strength woven in"],
  "follow_up_suggestion": "concrete follow-up timing and message if no reply in X days"
}}
"""

OUTREACH_TYPES = [
    "informational_interview",
    "referral_request",
    "job_inquiry",
    "networking",
    "thank_you_post_interview",
]


class OutreachResult:
    def __init__(self):
        self.subject: str = ""
        self.body: str = ""
        self.tone: str = "professional"
        self.word_count: int = 0
        self.personalization_hooks: list = []
        self.follow_up_suggestion: str = ""
        self.model_used: Optional[str] = None
        self.cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return self.__dict__


class OutreachService:

    async def generate_email(
        self,
        sender_name: str,
        current_role: str,
        target_role: str,
        key_strengths: list[str],
        recipient_name: str,
        recipient_title: str,
        company_name: str,
        goal: str = "informational_interview",
        context: str = "",
        user_id: Optional[str] = None,
        user_plan: str = "pro",
        sender_email: str = "",
        sender_linkedin: str = "",
        sender_phone: str = "",
    ) -> OutreachResult:
        result = OutreachResult()

        # Only pro users
        llm_decision = await cost_governor.can_use_llm(
            user_id or "anon", user_plan, "recruiter"
        )
        if not llm_decision["allowed"]:
            result.body = "Upgrade to Pro to generate personalized outreach emails."
            return result

        goal_instructions = GOAL_INSTRUCTIONS.get(
            goal, GOAL_INSTRUCTIONS["informational_interview"]
        )
        # Format key strengths as a readable list
        strengths_text = " | ".join(key_strengths[:5]) if key_strengths else "strong analytical and communication skills"

        prompt = OUTREACH_PROMPT.format(
            sender_name=sender_name,
            current_role=current_role or "professional",
            target_role=target_role,
            key_strengths=strengths_text,
            recipient_name=recipient_name,
            recipient_title=recipient_title or "professional",
            company_name=company_name,
            context=context or f"works at {company_name}",
            goal_instructions=goal_instructions,
        )

        try:
            llm_resp = await llm_client.complete(
                prompt, model="gemini-2.0-flash", max_tokens=1500, temperature=0.6
            )
            data = llm_resp.as_json()

            result.subject = data.get("subject", "")
            body = data.get("body", "")

            # Append professional signature
            sig_lines = [f"\n\nWarm regards,", sender_name or ""]
            if current_role:
                sig_lines.append(current_role)
            if sender_phone:
                sig_lines.append(sender_phone)
            if sender_email:
                sig_lines.append(sender_email)
            if sender_linkedin:
                sig_lines.append(sender_linkedin)
            result.body = body + "\n".join(sig_lines)

            result.tone = data.get("tone", "professional")
            result.word_count = data.get("word_count", 0)
            result.personalization_hooks = data.get("personalization_hooks", [])
            result.follow_up_suggestion = data.get("follow_up_suggestion", "")
            result.model_used = "gemini-2.0-flash"
            result.cost_usd = llm_resp.cost_usd

            if user_id:
                await cost_governor.record_spend(user_id, llm_resp.cost_usd)

        except Exception as e:
            logger.error(f"Outreach generation failed: {e}")
            result.body = "Failed to generate email. Please try again."

        return result

    async def generate_bulk(
        self,
        sender_profile: dict,
        recipients: list[dict],
        goal: str = "informational_interview",
        user_id: Optional[str] = None,
        user_plan: str = "pro",
    ) -> list[dict]:
        """Generate personalized emails for multiple recipients."""
        results = []
        for recipient in recipients[:10]:  # Max 10 at once
            result = await self.generate_email(
                sender_name=sender_profile.get("name", ""),
                current_role=sender_profile.get("current_role", ""),
                target_role=sender_profile.get("target_role", ""),
                key_strengths=sender_profile.get("key_strengths", []),
                recipient_name=recipient.get("name", ""),
                recipient_title=recipient.get("title", ""),
                company_name=recipient.get("company", ""),
                goal=goal,
                context=recipient.get("context", ""),
                user_id=user_id,
                user_plan=user_plan,
                sender_email=sender_profile.get("email", ""),
                sender_linkedin=sender_profile.get("linkedin_url", ""),
                sender_phone=sender_profile.get("phone", ""),
            )
            results.append({
                "recipient": recipient,
                "email": result.to_dict(),
            })
        return results


outreach_service = OutreachService()
