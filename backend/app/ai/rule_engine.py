"""
Rule Engine — deterministic analysis that runs before any AI call.
Fast, free, explainable. AI is only called when this is insufficient.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuleEngineResult:
    # Scores (0-100)
    keyword_score: float = 0.0
    format_score: float = 0.0
    length_score: float = 0.0

    # Keyword analysis
    required_keywords_found: list = field(default_factory=list)
    required_keywords_missing: list = field(default_factory=list)
    preferred_keywords_found: list = field(default_factory=list)
    preferred_keywords_missing: list = field(default_factory=list)
    keyword_density: dict = field(default_factory=dict)

    # Format issues
    format_issues: list = field(default_factory=list)
    format_positives: list = field(default_factory=list)

    # ATS red flags
    ats_red_flags: list = field(default_factory=list)

    # Seniority indicators
    detected_seniority: Optional[str] = None
    years_of_experience: Optional[int] = None

    # Overall confidence (can we skip LLM?)
    confidence: float = 0.0  # 0-1: high = skip LLM, low = need LLM


# Common ATS red flags
ATS_RED_FLAGS = [
    (r"<[^>]+>", "HTML tags detected — ATS cannot parse HTML resumes"),
    (r"[\u2022\u2023\u25E6\u2043]", "Special bullet characters may not parse in all ATS"),
    (r"header|footer", "Content in headers/footers may be ignored by ATS"),
]

# Seniority keywords
SENIORITY_SIGNALS = {
    "senior": ["senior", "lead", "principal", "staff", "architect"],
    "mid": ["engineer", "developer", "manager", "analyst"],
    "junior": ["junior", "associate", "entry", "intern", "trainee"],
    "executive": ["vp", "director", "cto", "cpo", "head of"],
}

# PM-specific skill taxonomy
PM_SKILLS = {
    "core_pm": ["product roadmap", "PRD", "user stories", "sprint", "agile", "scrum",
                "product strategy", "OKR", "KPI", "A/B test", "go-to-market", "GTM"],
    "ai_pm": ["machine learning", "ML", "AI", "model", "LLM", "NLP", "recommendation",
              "feature engineering", "data pipeline", "embeddings", "RAG"],
    "tpm": ["technical requirements", "API", "system design", "architecture",
             "engineering team", "technical roadmap", "infra"],
    "analytics": ["SQL", "Python", "data analysis", "metrics", "funnel", "cohort",
                  "retention", "tableau", "looker", "amplitude", "mixpanel"],
}


class RuleEngine:

    def analyze(self, resume_text: str, jd_text: Optional[str] = None) -> RuleEngineResult:
        result = RuleEngineResult()
        result.format_score = self._check_format(resume_text)
        result.length_score = self._check_length(resume_text)
        result.detected_seniority = self._detect_seniority(resume_text)
        result.years_of_experience = self._extract_years_experience(resume_text)
        result.ats_red_flags = self._check_ats_red_flags(resume_text)

        if jd_text:
            kw_result = self._analyze_keywords(resume_text, jd_text)
            result.required_keywords_found = kw_result["required_found"]
            result.required_keywords_missing = kw_result["required_missing"]
            result.preferred_keywords_found = kw_result["preferred_found"]
            result.preferred_keywords_missing = kw_result["preferred_missing"]
            result.keyword_score = kw_result["score"]
            result.keyword_density = kw_result["density"]

        # Compute confidence: high if keyword match is clear
        if jd_text:
            if result.keyword_score > 80 or result.keyword_score < 25:
                result.confidence = 0.9  # Clear result — skip LLM
            else:
                result.confidence = 0.3  # Ambiguous — needs LLM
        else:
            result.confidence = 0.7  # No JD — format/structure only

        return result

    def _check_format(self, text: str) -> float:
        score = 100.0
        issues = []
        positives = []

        # Length check
        word_count = len(text.split())
        if word_count < 200:
            score -= 20
            issues.append("Resume appears very short (< 200 words)")
        elif word_count > 1200:
            score -= 10
            issues.append("Resume may be too long for ATS (> 1200 words)")
        else:
            positives.append("Good length for ATS parsing")

        # Sections check
        important_sections = ["experience", "education", "skills"]
        for section in important_sections:
            if section.lower() not in text.lower():
                score -= 10
                issues.append(f"Missing '{section}' section")

        # Contact info
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.search(email_pattern, text):
            score -= 15
            issues.append("No email address detected")

        return max(0, min(100, score))

    def _check_length(self, text: str) -> float:
        word_count = len(text.split())
        # Optimal: 400-800 words
        if 400 <= word_count <= 800:
            return 100.0
        elif 300 <= word_count < 400 or 800 < word_count <= 1000:
            return 80.0
        elif 200 <= word_count < 300 or 1000 < word_count <= 1200:
            return 60.0
        else:
            return 40.0

    def _analyze_keywords(self, resume_text: str, jd_text: str) -> dict:
        resume_lower = resume_text.lower()

        jd_keywords = self._extract_keywords(jd_text)
        required_kw = jd_keywords[:15]   # Top 15 = "required"
        preferred_kw = jd_keywords[15:30]  # Next 15 = "preferred"

        required_found = [kw for kw in required_kw if self._kw_in_text(kw, resume_lower)]
        required_missing = [kw for kw in required_kw if not self._kw_in_text(kw, resume_lower)]
        preferred_found = [kw for kw in preferred_kw if self._kw_in_text(kw, resume_lower)]
        preferred_missing = [kw for kw in preferred_kw if not self._kw_in_text(kw, resume_lower)]

        if len(required_kw) == 0:
            keyword_score = 50.0
        else:
            required_pct = len(required_found) / len(required_kw)
            preferred_pct = len(preferred_found) / max(len(preferred_kw), 1)
            # More generous scoring: matching all required = 85, all preferred adds up to 15 more
            keyword_score = (required_pct * 85) + (preferred_pct * 15)

        density = {kw: resume_lower.count(kw.lower()) for kw in required_found}

        return {
            "required_found": required_found,
            "required_missing": required_missing,
            "preferred_found": preferred_found,
            "preferred_missing": preferred_missing,
            "score": round(keyword_score, 1),
            "density": density,
        }

    def _kw_in_text(self, kw: str, text_lower: str) -> bool:
        """Check keyword presence with word-boundary awareness for short terms."""
        kw_l = kw.lower()
        if kw_l not in text_lower:
            return False
        # For short acronyms/terms (≤5 chars), require word boundary to avoid false matches
        if len(kw_l) <= 5:
            return bool(re.search(r'\b' + re.escape(kw_l) + r'\b', text_lower))
        return True

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract single-word and compound tech keywords from JD text.
        Avoids long phrases — substring matching works best on short terms."""
        stop_words = {
            "the", "and", "for", "with", "this", "that", "have", "will",
            "from", "they", "their", "what", "when", "where", "which",
            "able", "also", "into", "been", "more", "some", "than",
            "both", "each", "such", "your", "about", "other", "these",
            "work", "team", "role", "join", "help", "make", "build",
            "looking", "seeking", "required", "preferred", "strong",
            "excellent", "good", "great", "using", "used", "across",
        }

        # Extract individual words (no spaces) — most reliable for matching
        single_words = re.findall(r'\b[A-Za-z][A-Za-z0-9+#.-]{2,25}\b', text)
        # Extract explicit 2-word technical phrases (CamelCase or Title Case or known patterns)
        two_word = re.findall(
            r'\b(?:[A-Z][a-z]+|[A-Z]{2,})\s+(?:[A-Z][a-z]+|[A-Z]{2,})\b', text
        )

        seen = set()
        keywords = []

        for w in single_words:
            w_l = w.lower()
            if w_l not in stop_words and len(w_l) >= 3 and w_l not in seen:
                seen.add(w_l)
                keywords.append(w_l)

        for phrase in two_word:
            p_l = phrase.lower()
            if p_l not in seen and len(p_l) > 6:
                seen.add(p_l)
                keywords.append(p_l)

        # Score by frequency in JD
        text_lower = text.lower()
        freq = {kw: text_lower.count(kw) for kw in keywords}
        sorted_kw = sorted(keywords, key=lambda k: freq[k], reverse=True)
        return sorted_kw[:30]

    def _detect_seniority(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for level, signals in SENIORITY_SIGNALS.items():
            if any(signal in text_lower for signal in signals):
                return level
        return "mid"

    def _extract_years_experience(self, text: str) -> Optional[int]:
        patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'(\d+)\+?\s*years?\s+in',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _check_ats_red_flags(self, text: str) -> list[str]:
        flags = []
        for pattern, message in ATS_RED_FLAGS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(message)
        return flags


rule_engine = RuleEngine()
