"""
Job Suggestions Service — AI-generated job matches based on resume + target roles.
Premium feature (Pro plan only).
"""
import logging
import json
import uuid
from typing import Optional

from app.ai.llm_client import llm_client

logger = logging.getLogger(__name__)

JOB_GENERATION_PROMPT = """
You are a job market expert. Based on this resume summary and target roles, generate realistic job listings
that this person would be a strong match for.

RESUME SUMMARY (first 2000 chars):
{resume_text}

TARGET ROLES: {target_roles}
LOCATION PREFERENCE: {location}

Generate {count} realistic job listings. For each job, include a fit score (0-100) based on how well the resume matches.
Make company names, titles, and descriptions realistic and specific.

Return JSON array:
[
  {{
    "job_id": "unique_id",
    "title": "job title",
    "company": "company name",
    "location": "city, state or Remote",
    "remote": true/false,
    "url": "https://linkedin.com/jobs/view/12345",
    "snippet": "2-3 sentence job description focusing on key responsibilities",
    "fit_score": 75,
    "fit_reason": "Why this is a good match in one sentence",
    "posted_date": "2 days ago"
  }}
]

Rules:
- Mix of remote and on-site roles
- Vary fit scores realistically (50-95 range)
- Use real company names (tech companies, startups, enterprises)
- Match seniority level to the resume experience
- Make snippets specific, not generic
"""


class JobMatch:
    def __init__(self):
        self.job_id: str = ""
        self.title: str = ""
        self.company: str = ""
        self.location: str = ""
        self.remote: bool = False
        self.url: str = ""
        self.snippet: str = ""
        self.salary_min: Optional[int] = None
        self.salary_max: Optional[int] = None
        self.posted_date: str = ""
        self.fit_score: float = 0.0
        self.fit_reason: str = ""
        self.source: str = "ai"

    def to_dict(self) -> dict:
        return self.__dict__


class JobSuggestionsService:

    async def get_suggestions(
        self,
        resume_text: str,
        target_roles: list[str],
        location: str = "Remote",
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Generate AI-matched job suggestions based on resume and target roles.
        """
        try:
            prompt = JOB_GENERATION_PROMPT.format(
                resume_text=resume_text[:2000],
                target_roles=", ".join(target_roles[:3]),
                location=location,
                count=min(limit, 15),
            )

            llm_resp = await llm_client.complete(
                prompt, model="gemini-2.5-flash-lite", max_tokens=3000, temperature=0.7
            )
            jobs_data = llm_resp.as_json()

            if not isinstance(jobs_data, list):
                logger.warning("Job generation returned non-list response")
                return []

            jobs = []
            for item in jobs_data:
                job = JobMatch()
                job.job_id = item.get("job_id", str(uuid.uuid4())[:8])
                job.title = item.get("title", "")
                job.company = item.get("company", "")
                job.location = item.get("location", location)
                job.remote = item.get("remote", False)
                job.url = item.get("url", "https://linkedin.com/jobs")
                job.snippet = item.get("snippet", "")
                job.fit_score = float(item.get("fit_score", 60))
                job.fit_reason = item.get("fit_reason", "")
                job.posted_date = item.get("posted_date", "Recently posted")
                jobs.append(job)

            # Sort by fit score
            jobs.sort(key=lambda j: j.fit_score, reverse=True)
            return [j.to_dict() for j in jobs[:limit]]

        except Exception as e:
            logger.error(f"Job suggestion generation failed: {e}")
            return []


job_suggestions_service = JobSuggestionsService()
