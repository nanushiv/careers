"""
Job Suggestions Service — fetches real PM jobs from Jobicy (primary) + Remotive (secondary),
scores them against the user's resume using keyword overlap.
No LLM needed; fully deterministic and free.
"""
import re
import asyncio
import logging
import httpx
from datetime import date
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

ADZUNA_APP_ID = settings.ADZUNA_APP_ID
ADZUNA_APP_KEY = settings.ADZUNA_APP_KEY

# Differentiating terms only — generic PM words (roadmap, strategy, stakeholder etc.) removed
# because they appear in every PM resume AND every PM JD, causing 98% for all jobs.
# These terms are specific enough to actually differentiate matches.
HIGH_SIGNAL_TERMS = {
    # Technical / data
    "sql", "python", "api", "llm", "ai", "ml", "nlp", "data science",
    "machine learning", "deep learning", "tableau", "amplitude", "mixpanel",
    "looker", "bigquery", "snowflake", "spark", "tensorflow", "pytorch",
    "ab testing", "experimentation", "statistics",
    # Domain
    "fintech", "healthtech", "edtech", "proptech", "insurtech", "legaltech",
    "b2b", "b2c", "saas", "enterprise", "marketplace", "platform",
    "consumer", "ecommerce", "payments", "lending", "banking", "insurance",
    # Product specifics
    "growth", "monetization", "pricing", "revenue", "retention", "conversion",
    "onboarding", "activation", "engagement", "funnel", "cohort",
    "search", "recommendation", "ads", "notifications", "checkout",
    # Tools
    "figma", "jira", "confluence", "notion", "amplitude", "segment",
    "salesforce", "hubspot", "zendesk",
    # Soft differentiators
    "0 to 1", "zero to one", "founding", "startup", "seed", "series",
    "technical pm", "staff pm", "principal pm", "director", "vp product",
    "mobile", "ios", "android", "web", "infrastructure", "developer tools",
    "open source", "api-first", "developer", "devtools",
}

STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "have", "will", "from",
    "they", "their", "what", "when", "where", "which", "able", "also",
    "into", "been", "more", "some", "than", "both", "each", "such",
    "your", "about", "other", "these", "work", "team", "role", "join",
    "help", "make", "build", "looking", "seeking", "required", "preferred",
    "strong", "excellent", "good", "great", "using", "used", "across",
    "you", "our", "are", "can", "not", "all", "but", "its", "has",
    "who", "how", "may", "new", "two", "way", "get", "see", "one",
    "off", "per", "any", "use", "own", "set", "put", "run", "ask",
    "including", "ensure", "experience", "ability", "skills", "working",
}

PM_TITLE_PHRASES = [
    "product manager", "product management", "product lead", "product owner",
    "senior pm", "staff pm", "principal pm", "group pm",
    "ai product", "technical product manager", "tpm",
    "head of product", "vp of product", "vp product",
    "director of product", "chief product", "cpo",
]


def _title_is_pm(title: str) -> bool:
    return any(phrase in title.lower() for phrase in PM_TITLE_PHRASES)


def _title_matches_target(title: str, target_roles: list[str]) -> bool:
    t = title.lower()
    return any(role.lower() in t for role in target_roles) or _title_is_pm(title)


def _extract_keywords(text: str) -> set[str]:
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.\-]{2,}\b', text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) >= 3}


def _score_job(resume_text: str, job_title: str, job_description: str) -> tuple[float, str]:
    resume_kws = _extract_keywords(resume_text)
    jd_kws = _extract_keywords(f"{job_title} {job_description}")

    resume_signal = resume_kws & HIGH_SIGNAL_TERMS
    jd_signal = jd_kws & HIGH_SIGNAL_TERMS

    if not jd_signal:
        base_score = 25.0
        matched = set()
    else:
        matched = resume_signal & jd_signal
        # Recall-based: % of JD signal terms covered by resume
        base_score = len(matched) / max(len(jd_signal), 1) * 100

    title_bonus = 15 if _title_is_pm(job_title) else 0
    score = min(98.0, round(base_score + title_bonus, 1))

    top_matched = sorted(matched, key=len, reverse=True)[:3]
    if top_matched:
        matched_str = ", ".join(top_matched)
        missing = sorted(jd_signal - resume_signal, key=len, reverse=True)[:1]
        reason = f"Matches on {matched_str}" + (f"; adding '{missing[0]}' could help" if missing else "")
    else:
        reason = "Limited overlap — consider tailoring your resume for this role"

    return score, reason


GEO_MAP = {
    "india": "india",
    "usa": "usa", "united states": "usa", "us": "usa", "america": "usa",
    "uk": "uk", "united kingdom": "uk", "england": "uk", "britain": "uk",
    "canada": "canada",
    "australia": "australia",
    "germany": "germany", "deutschland": "germany",
    "france": "france",
    "spain": "spain",
    "netherlands": "netherlands", "holland": "netherlands",
    "singapore": "singapore",
    "europe": "europe",
    "brazil": "brazil",
    "poland": "poland",
    "portugal": "portugal",
    "japan": "japan",
    "israel": "israel",
    "ukraine": "ukraine",
    "serbia": "serbia",
}

# Adzuna country codes (for country-specific job search)
ADZUNA_COUNTRY_MAP = {
    "india": "in",
    "usa": "us", "united states": "us", "us": "us", "america": "us",
    "uk": "gb", "united kingdom": "gb", "england": "gb", "britain": "gb",
    "canada": "ca",
    "australia": "au",
    "germany": "de", "deutschland": "de",
    "france": "fr",
    "spain": "es",
    "netherlands": "nl", "holland": "nl",
    "singapore": "sg",
    "brazil": "br",
    "poland": "pl",
    "south africa": "za",
    "new zealand": "nz",
    "austria": "at",
    "belgium": "be",
    "italy": "it",
    "mexico": "mx",
}

# Major cities → Adzuna country code
CITY_TO_ADZUNA = {
    "london": "gb", "manchester": "gb", "birmingham": "gb", "glasgow": "gb",
    "new york": "us", "san francisco": "us", "los angeles": "us", "chicago": "us",
    "seattle": "us", "boston": "us", "austin": "us", "new york city": "us",
    "nyc": "us", "sf": "us",
    "toronto": "ca", "vancouver": "ca", "montreal": "ca",
    "sydney": "au", "melbourne": "au", "brisbane": "au", "perth": "au",
    "bangalore": "in", "bengaluru": "in", "mumbai": "in", "delhi": "in",
    "hyderabad": "in", "pune": "in", "chennai": "in", "gurgaon": "in",
    "berlin": "de", "munich": "de", "hamburg": "de", "frankfurt": "de",
    "paris": "fr", "lyon": "fr",
    "amsterdam": "nl", "rotterdam": "nl",
    "dubai": "ae", "abu dhabi": "ae",
}

# Keywords in job location that indicate a job is truly in the given Adzuna country
ADZUNA_COUNTRY_LOCATION_KEYWORDS: dict[str, tuple] = {
    "au": ("australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra", "queensland", "victoria", "nsw"),
    "in": ("india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "pune", "chennai", "gurgaon", "noida"),
    "us": ("united states", "new york", "san francisco", "los angeles", "chicago", "boston", "austin", "seattle", "atlanta", "dallas", "denver", "remote", "usa"),
    "gb": ("uk", "united kingdom", "london", "manchester", "birmingham", "england", "scotland", "wales", "remote"),
    "ca": ("canada", "toronto", "vancouver", "montreal", "calgary", "ottawa", "remote"),
    "de": ("germany", "berlin", "munich", "hamburg", "frankfurt", "cologne", "remote"),
    "fr": ("france", "paris", "lyon", "marseille", "remote"),
    "sg": ("singapore",),
    "nl": ("netherlands", "amsterdam", "rotterdam", "remote"),
    "br": ("brazil", "são paulo", "sao paulo", "rio", "remote"),
    "nz": ("new zealand", "auckland", "wellington", "remote"),
    "pl": ("poland", "warsaw", "krakow", "remote"),
    "es": ("spain", "madrid", "barcelona", "remote"),
    "it": ("italy", "rome", "milan", "remote"),
    "at": ("austria", "vienna", "remote"),
    "be": ("belgium", "brussels", "remote"),
    "za": ("south africa", "johannesburg", "cape town", "remote"),
    "mx": ("mexico", "mexico city", "remote"),
    "ae": ("dubai", "abu dhabi", "uae", "remote"),
}


def _word_match(key: str, text: str) -> bool:
    """True if `key` appears as a whole word (or phrase) in `text`."""
    return bool(re.search(r'\b' + re.escape(key) + r'\b', text))


def _location_to_geo(location: str) -> Optional[str]:
    """Map free-text location to Jobicy geo slug. Returns None for Remote/Worldwide."""
    loc = location.lower().strip()
    if not loc or loc in ("remote", "worldwide", "anywhere", "global"):
        return None
    for key, val in GEO_MAP.items():
        if _word_match(key, loc):
            return val
    return None


def _location_to_adzuna_country(location: str) -> Optional[str]:
    """Map free-text location to Adzuna 2-letter country code."""
    loc = location.lower().strip()
    if not loc or loc in ("remote", "worldwide", "anywhere", "global"):
        return None
    for key, val in ADZUNA_COUNTRY_MAP.items():
        if _word_match(key, loc):
            return val
    # Try city-to-country fallback
    for city, code in CITY_TO_ADZUNA.items():
        if _word_match(city, loc):
            return code
    return None


def _adzuna_job_in_country(job_location: str, adzuna_country: str) -> bool:
    """Return True if Adzuna job's location is actually in the requested country or remote."""
    jl = job_location.lower()
    keywords = ADZUNA_COUNTRY_LOCATION_KEYWORDS.get(adzuna_country, ())
    if not keywords:
        return True  # Unknown country — let it through
    return any(kw in jl for kw in keywords)


def _job_location_matches(job_location: str, requested_location: str) -> bool:
    """Return True if the job's location is acceptable for the requested location.
    Always accepts remote/worldwide jobs. For specific countries, checks for a match."""
    jl = job_location.lower().strip()
    # Always include remote/worldwide jobs
    if any(w in jl for w in ("remote", "worldwide", "anywhere", "global", "")):
        return True
    # Check if job location mentions the requested country
    rl = requested_location.lower().strip()
    geo = _location_to_geo(rl)
    if geo and geo in jl:
        return True
    # Direct substring match
    for key in GEO_MAP:
        if key in rl and key in jl:
            return True
    return False


class JobSuggestionsService:

    async def get_suggestions(
        self,
        resume_text: str,
        target_roles: list[str],
        location: str = "Remote",
        limit: int = 20,
        user_id: Optional[str] = None,
        user_yoe: Optional[int] = None,
    ) -> dict:
        """
        Fetch real PM jobs. Sources (in order):
        1. Jobicy — fresh remote + geo-filtered PM jobs, free API, no key
        2. Remotive — remote PM jobs, free API, no key
        Returns {"jobs": [...], "location_note": str|None}
        """
        normalized: list[dict] = []
        geo_normalized: list[dict] = []
        seen_keys: set[str] = set()
        geo = _location_to_geo(location)
        adzuna_country = _location_to_adzuna_country(location)
        location_requested = location.strip() if location else ""
        is_worldwide_search = not location_requested or location_requested.lower() in (
            "remote", "worldwide", "anywhere", "global", ""
        )

        async with httpx.AsyncClient(timeout=12.0) as client:

            async def fetch_adzuna(query: str):
                try:
                    r = await client.get(
                        f"https://api.adzuna.com/v1/api/jobs/{adzuna_country}/search/1",
                        params={"app_id": ADZUNA_APP_ID, "app_key": ADZUNA_APP_KEY,
                                "what": query, "results_per_page": 30, "sort_by": "date"},
                    )
                    return ("adzuna", r.json().get("results", []) if r.status_code == 200 else [])
                except Exception as e:
                    logger.warning(f"Adzuna fetch failed ({query}): {e}")
                    return ("adzuna", [])

            async def fetch_jobicy(tag: str):
                try:
                    r = await client.get(
                        "https://jobicy.com/api/v2/remote-jobs",
                        params={"count": 50, "tag": tag},
                    )
                    return ("jobicy", r.json().get("jobs", []) if r.status_code == 200 else [])
                except Exception as e:
                    logger.warning(f"Jobicy fetch failed ({tag}): {e}")
                    return ("jobicy", [])

            async def fetch_remotive():
                try:
                    r = await client.get(
                        "https://remotive.com/api/remote-jobs",
                        params={"category": "product", "limit": 100},
                    )
                    return ("remotive", r.json().get("jobs", []) if r.status_code == 200 else [])
                except Exception as e:
                    logger.warning(f"Remotive fetch failed: {e}")
                    return ("remotive", [])

            # Build all tasks and run concurrently
            # Specific location → Adzuna only (country-specific jobs)
            # Remote/worldwide → Jobicy + Remotive (remote boards)
            tasks = []
            if not is_worldwide_search:
                # Location-specific search: only use Adzuna (real country jobs)
                if adzuna_country and ADZUNA_APP_ID and ADZUNA_APP_KEY:
                    tasks += [fetch_adzuna("product manager"), fetch_adzuna("senior product manager")]
                # No Jobicy/Remotive — they are remote-only boards and pollute results
            else:
                # Remote/worldwide search: use remote boards only
                tasks += [
                    fetch_jobicy("product manager"),
                    fetch_jobicy("product management"),
                    fetch_jobicy("senior product manager"),
                    fetch_remotive(),
                ]
            results = await asyncio.gather(*tasks)

            # Merge results
            for source, jobs in results:
                for job in jobs:
                    if source == "adzuna":
                        n = _normalize_adzuna(job)
                        is_geo = True
                    elif source == "jobicy":
                        n = _normalize_jobicy(job)
                        is_geo = False
                    else:
                        n = _normalize_remotive(job)
                        is_geo = False
                    if n:
                        if not is_worldwide_search:
                            if is_geo and adzuna_country:
                                # Filter Adzuna results: only keep jobs actually in the country or remote
                                if not _adzuna_job_in_country(n["location"], adzuna_country):
                                    continue
                            elif not is_geo:
                                if not _job_location_matches(n["location"], location_requested):
                                    continue
                        k = f"{n['title'].lower()}|{n['company'].lower()}"
                        if k not in seen_keys:
                            seen_keys.add(k)
                            normalized.append(n)
                            if is_geo:
                                geo_normalized.append(n)

        # Build location note
        location_note: Optional[str] = None
        if not is_worldwide_search:
            if not adzuna_country:
                location_note = f"'{location_requested.title()}' not recognized. Try a country name: India, UK, USA, Canada, Australia, Germany, Singapore. Or type 'Remote' for worldwide."
            elif len(normalized) == 0:
                location_note = f"No PM jobs found in {location_requested.title()} right now. Try 'Remote' for worldwide jobs."

        if not normalized:
            return {"jobs": [], "location_note": location_note}

        # Filter to PM-relevant titles
        relevant = [j for j in normalized if _title_matches_target(j["title"], target_roles)]
        if len(relevant) < 5:
            relevant = normalized[:40]

        # Score and sort
        scored = []
        for job in relevant:
            fit_score, fit_reason = _score_job(resume_text, job["title"], job["desc"])
            yoe_required = _extract_yoe(job["desc"] + " " + job["title"])
            yoe_label = _yoe_label(yoe_required, user_yoe)
            scored.append({
                "job_id": job["job_id"],
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "remote": job.get("remote", True),
                "url": job["url"],
                "snippet": _clean_snippet(job["desc"]),
                "fit_score": fit_score,
                "fit_reason": fit_reason,
                "posted_date": _format_date(job["pub"]),
                "tags": job["tags"],
                "yoe_required": yoe_required,
                "yoe_label": yoe_label,
            })

        scored.sort(key=lambda j: j["fit_score"], reverse=True)
        return {"jobs": scored[:limit], "location_note": location_note}


def _normalize_jobicy(job: dict) -> Optional[dict]:
    title = job.get("jobTitle") or ""
    company = job.get("companyName") or ""
    if not title or not company:
        return None
    return {
        "job_id": str(job.get("id", ""))[:24],
        "title": title,
        "company": company,
        "location": job.get("jobGeo") or "Remote",
        "remote": True,  # Jobicy is a remote-only board
        "url": job.get("url") or job.get("jobExcerpt") or "",
        "desc": job.get("jobExcerpt") or "",
        "pub": (job.get("pubDate") or "")[:10],
        "tags": (job.get("jobIndustry") if isinstance(job.get("jobIndustry"), list) else str(job.get("jobIndustry") or "").split(","))[:3],
    }


def _normalize_remotive(job: dict) -> Optional[dict]:
    title = job.get("title") or ""
    company = job.get("company_name") or ""
    if not title or not company:
        return None
    raw_tags = job.get("tags") or []
    tags = [t if isinstance(t, str) else t.get("label", "") for t in raw_tags][:5]
    return {
        "job_id": str(job.get("id", ""))[:24],
        "title": title,
        "company": company,
        "location": job.get("candidate_required_location") or "Remote",
        "remote": True,  # Remotive is a remote-only board
        "url": job.get("url") or "",
        "desc": job.get("description") or "",
        "pub": (job.get("publication_date") or "")[:10],
        "tags": tags,
    }


def _normalize_adzuna(job: dict) -> Optional[dict]:
    title = job.get("title") or ""
    company = (job.get("company") or {}).get("display_name") or ""
    if not title or not company:
        return None
    location_parts = job.get("location", {}).get("area", [])
    location = ", ".join(location_parts[-2:]) if location_parts else "Unknown"
    # Detect remote: check title and location text
    text_lower = f"{title} {location}".lower()
    is_remote = any(w in text_lower for w in ("remote", "work from home", "wfh", "anywhere"))
    return {
        "job_id": str(job.get("id", ""))[:24],
        "title": title,
        "company": company,
        "location": location,
        "remote": is_remote,
        "url": job.get("redirect_url") or "",
        "desc": job.get("description") or "",
        "pub": (job.get("created") or "")[:10],
        "tags": [],
    }


def _clean_snippet(html: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", html)
    plain = re.sub(r"\s+", " ", plain).strip()
    return (plain[:220] + "…") if len(plain) > 220 else plain


def _extract_yoe(text: str) -> Optional[int]:
    """Extract minimum required years of experience from job text."""
    # Patterns: "5+ years", "5-8 years", "minimum 5 years", "at least 5 years"
    patterns = [
        r'(\d+)\s*\+\s*years?',
        r'(\d+)\s*-\s*\d+\s*years?',
        r'(?:minimum|at least|min\.?)\s+(\d+)\s*years?',
        r'(\d+)\s*years?\s+of\s+(?:professional\s+)?experience',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return int(m.group(1))
    return None


def _yoe_label(yoe_required: Optional[int], user_yoe: Optional[int]) -> Optional[str]:
    """Return a badge label comparing required vs user's YOE. Green if within +4 years."""
    if yoe_required is None:
        return None
    if user_yoe is None:
        return f"{yoe_required}+ YOE required"
    if yoe_required <= user_yoe + 6:
        return f"✓ {yoe_required}+ YOE (you have {user_yoe})"
    return f"⚡ Stretch — {yoe_required}+ YOE (you have {user_yoe})"


def _format_date(iso_date: str) -> str:
    if not iso_date:
        return "Recently posted"
    try:
        posted = date.fromisoformat(iso_date)
        delta = (date.today() - posted).days
        if delta == 0: return "Today"
        if delta == 1: return "Yesterday"
        if delta < 7: return f"{delta} days ago"
        if delta < 30: return f"{delta // 7}w ago"
        return f"{delta // 30}mo ago"
    except Exception:
        return "Recently posted"


job_suggestions_service = JobSuggestionsService()
