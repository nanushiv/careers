"""
Prompt templates — versioned, centralized, never hardcoded in services.
All prompts return JSON objects unless noted.
"""

PROMPTS = {

    # ── ATS Analysis ──────────────────────────────────────────────────────────
    "ats_enrichment_v1": """
You are an ATS (Applicant Tracking System) expert analyzing a resume against a job description.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{jd_text}

RULE ENGINE PRE-ANALYSIS:
{rule_engine_output}

The rule engine has already identified keyword gaps and format issues. Your job is to:
1. Add nuanced context to the gaps (why they matter for THIS role)
2. Identify semantic/conceptual gaps the rule engine may have missed
3. Assess the narrative coherence of the resume for this role
4. Score experience relevance (not just keyword presence)

Return JSON only:
{{
  "ats_score_adjustment": -10 to +10,
  "semantic_gaps": [
    {{"gap": "string", "severity": "critical|high|medium|low", "context": "why this matters"}}
  ],
  "narrative_coherence": {{
    "score": 0-100,
    "issue": "string or null",
    "recommendation": "string"
  }},
  "experience_relevance": {{
    "score": 0-100,
    "strongest_match": "string",
    "weakest_area": "string"
  }},
  "quick_fixes": [
    {{"action": "string", "impact": "high|medium|low", "effort": "minutes|hours|days"}}
  ]
}}
""",

    # ── Recruiter Perception ──────────────────────────────────────────────────
    "recruiter_perception_v2": """
You are a senior technical recruiter at a top tech company who has reviewed 10,000+ resumes.
You are evaluating a candidate for a {role_category} position ({role_level} level).

CANDIDATE RESUME (first-pass read — 30 seconds):
{resume_text}

ROLE REQUIREMENTS:
{jd_requirements}

Simulate exactly how you would perceive this candidate in the first 30 seconds of reviewing their resume.
Be honest, specific, and constructive — not generic.

Return JSON only:
{{
  "perception_score": 0-100,
  "first_impression": "1-2 sentence immediate reaction",
  "likelihood_to_shortlist": "low|medium|high|very_high",
  "standout_positives": [
    {{"point": "string", "why_it_matters": "string"}}
  ],
  "immediate_concerns": [
    {{"concern": "string", "severity": "dealbreaker|major|minor", "context": "string"}}
  ],
  "positioning_gaps": [
    {{"gap": "string", "what_recruiter_thinks": "string", "how_to_fix": "string"}}
  ],
  "narrative_story": "The story a recruiter would construct about this candidate in 2-3 sentences",
  "vs_typical_applicant": "How does this candidate compare to the average applicant pool?",
  "recommended_resume_changes": [
    {{"change": "string", "before_example": "string", "after_example": "string"}}
  ],
  "interview_likelihood_rationale": "Why would/wouldn't a recruiter move this forward?"
}}
""",

    # ── Role Fit Analysis ─────────────────────────────────────────────────────
    "role_fit_enrichment_v1": """
You are a hiring manager evaluating candidate fit for a specific role.

CANDIDATE PROFILE:
{resume_sections}

TARGET ROLE:
{role_details}

SEMANTIC SIMILARITY SCORE (computed): {semantic_score}/100

Provide nuanced fit analysis beyond keyword matching:

Return JSON only:
{{
  "role_fit_score": 0-100,
  "fit_rationale": "2-3 sentences explaining the fit/mis-fit",
  "dimension_scores": {{
    "technical_skills": 0-100,
    "domain_experience": 0-100,
    "scope_and_scale": 0-100,
    "culture_signals": 0-100,
    "growth_trajectory": 0-100
  }},
  "strongest_alignment": ["top 3 alignment points"],
  "critical_gaps": [
    {{"gap": "string", "bridgeable": true/false, "bridge_path": "string"}}
  ],
  "positioning_advice": "How should candidate position themselves for this specific role?",
  "application_recommendation": "apply_strong|apply_with_improvements|stretch_role|not_recommended"
}}
""",

    # ── PM/AI Readiness Scoring ───────────────────────────────────────────────
    "pm_readiness_v1": """
You are an expert PM coach evaluating a candidate's readiness to transition into Product Management.

CANDIDATE BACKGROUND:
{resume_text}

TARGET ROLE TYPE: {target_role_type}
(e.g., "AI Product Manager", "Technical PM", "Consumer PM")

Evaluate PM readiness across these dimensions with honest, specific assessment:

Return JSON only:
{{
  "overall_readiness_score": 0-100,
  "readiness_level": "not_ready|developing|ready|strong",
  "dimensions": {{
    "product_thinking": {{
      "score": 0-100,
      "evidence_found": ["strings from resume"],
      "gaps": ["what's missing"],
      "development_actions": ["specific things to do"]
    }},
    "technical_credibility": {{
      "score": 0-100,
      "evidence_found": ["strings"],
      "gaps": ["what's missing"],
      "development_actions": ["actions"]
    }},
    "data_and_analytics": {{
      "score": 0-100,
      "evidence_found": ["strings"],
      "gaps": ["what's missing"],
      "development_actions": ["actions"]
    }},
    "stakeholder_influence": {{
      "score": 0-100,
      "evidence_found": ["strings"],
      "gaps": ["what's missing"],
      "development_actions": ["actions"]
    }},
    "ai_ml_fluency": {{
      "score": 0-100,
      "evidence_found": ["strings"],
      "gaps": ["what's missing"],
      "development_actions": ["actions"]
    }},
    "delivery_and_execution": {{
      "score": 0-100,
      "evidence_found": ["strings"],
      "gaps": ["what's missing"],
      "development_actions": ["actions"]
    }}
  }},
  "positioning_narrative": "How should this person pitch themselves as a PM candidate?",
  "critical_missing_experiences": ["top 3 things missing"],
  "quick_wins_30_days": ["achievable actions in 30 days"],
  "estimated_readiness_timeline": "Now|3 months|6 months|12 months"
}}
""",

    # ── Interview Question Generation ─────────────────────────────────────────
    "interview_questions_v2": """
Generate targeted interview preparation questions for this candidate applying to this role.

CANDIDATE PROFILE:
{resume_summary}

TARGET ROLE: {role_title} at {company_name}
INTERVIEW STAGE: {interview_stage}

Generate questions a skilled interviewer WOULD ask THIS specific candidate (not generic questions).
Focus on: likely probing points from their resume + core role competencies.

Return JSON only:
{{
  "questions": [
    {{
      "question": "string",
      "type": "behavioral|product|technical|analytical|leadership|culture",
      "difficulty": "easy|medium|hard",
      "why_theyll_ask_this": "string",
      "strong_answer_framework": "string (STAR, metrics-driven, etc.)",
      "red_flag_to_avoid": "string",
      "example_strong_opening": "string"
    }}
  ],
  "key_themes_to_prepare": ["top 4 themes"],
  "resume_weak_points_likely_probed": ["specific points from resume that will be challenged"],
  "one_question_to_nail": "The single most important question to prepare perfectly"
}}
""",

    # ── Weekly Insight Synthesis ──────────────────────────────────────────────
    "weekly_synthesis_v1": """
You are a strategic career advisor reviewing a job seeker's week.

USER PROFILE:
- Transitioning from: {current_role}
- Target roles: {target_roles}
- Weeks into job search: {weeks_searching}

WEEK {week_number} DATA:
- Applications submitted: {apps_this_week}
- Stage changes: {stage_changes}
- Callback rate this week: {callback_rate}%
- Cumulative callback rate: {cumulative_callback_rate}%
- Interviews scheduled: {interviews_scheduled}
- Current pipeline: {pipeline_summary}

PREVIOUS INSIGHTS (don't repeat these): {previous_insight_titles}

Generate 3 strategic insights. Be honest, specific, and actionable. Avoid generic career advice.
Focus on patterns, momentum signals, and strategic pivots.

Return JSON only:
{{
  "insights": [
    {{
      "type": "callback_pattern|positioning_gap|burnout_signal|momentum|strategic_pivot",
      "priority": "critical|high|medium",
      "title": "Short, specific title (not generic)",
      "summary": "1-2 sentence insight",
      "detail": "Detailed explanation with specific data points from their situation",
      "action": "Specific action to take this week",
      "impact": "Expected outcome if they follow this",
      "data_basis": "What data point triggered this insight"
    }}
  ]
}}
""",
}

# Prompt version registry — track which prompts are in production
ACTIVE_VERSIONS = {
    "ats": "ats_enrichment_v1",
    "recruiter": "recruiter_perception_v2",
    "role_fit": "role_fit_enrichment_v1",
    "readiness": "pm_readiness_v1",
    "interview_questions": "interview_questions_v2",
    "weekly_synthesis": "weekly_synthesis_v1",
}


def get_prompt(analysis_type: str) -> str:
    version = ACTIVE_VERSIONS.get(analysis_type)
    if not version:
        raise ValueError(f"No prompt found for analysis_type: {analysis_type}")
    return PROMPTS[version]
