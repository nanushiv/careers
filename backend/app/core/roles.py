"""
Role taxonomy — covers all career transition personas, not just PM.
Used across onboarding, readiness scoring, job suggestions, and prompts.
"""

FROM_ROLES = [
    "Software Engineer",
    "Senior Software Engineer",
    "Data Scientist",
    "Data Analyst",
    "Business Analyst",
    "Management Consultant",
    "Strategy Consultant",
    "UX Designer",
    "Marketing Manager",
    "MBA Graduate",
    "Operations Manager",
    "Finance / Investment Banking",
    "Non-tech background",
    "Other",
]

TARGET_ROLES = [
    # Product
    "Associate Product Manager (APM)",
    "Product Manager",
    "Senior Product Manager",
    "Group Product Manager",
    "Director of Product",
    "Chief Product Officer (CPO)",

    # AI / Technical
    "AI Product Manager",
    "Technical Product Manager (TPM)",
    "ML Product Manager",

    # Adjacent
    "Product Marketing Manager",
    "Growth Manager",
    "Strategy & Operations",
    "Chief of Staff",
    "Founder / Startup",
]

# Map target role → readiness dimensions to evaluate
ROLE_READINESS_DIMENSIONS = {
    "default": [
        "strategic_thinking",
        "communication",
        "data_analytics",
        "stakeholder_management",
        "execution_delivery",
        "domain_knowledge",
    ],
    "AI Product Manager": [
        "ai_ml_fluency",
        "technical_credibility",
        "data_analytics",
        "product_thinking",
        "stakeholder_management",
        "execution_delivery",
    ],
    "Technical Product Manager (TPM)": [
        "technical_credibility",
        "engineering_collaboration",
        "data_analytics",
        "execution_delivery",
        "stakeholder_management",
        "product_thinking",
    ],
    "Growth Manager": [
        "data_analytics",
        "experimentation",
        "product_thinking",
        "marketing_fluency",
        "execution_delivery",
        "stakeholder_management",
    ],
}

# Job search keywords per target role
ROLE_SEARCH_KEYWORDS = {
    "Associate Product Manager (APM)": ["associate product manager", "APM", "junior product manager"],
    "Product Manager": ["product manager", "PM"],
    "Senior Product Manager": ["senior product manager", "senior PM"],
    "Group Product Manager": ["group product manager", "GPM", "lead product manager"],
    "Director of Product": ["director of product", "director product management"],
    "Chief Product Officer (CPO)": ["chief product officer", "CPO", "VP product"],
    "AI Product Manager": ["AI product manager", "ML product manager", "AI PM"],
    "Technical Product Manager (TPM)": ["technical product manager", "TPM"],
    "ML Product Manager": ["machine learning product manager", "ML PM"],
    "Product Marketing Manager": ["product marketing manager", "PMM"],
    "Growth Manager": ["growth manager", "growth product manager", "growth PM"],
    "Strategy & Operations": ["strategy operations", "strategy and ops", "bizops"],
    "Chief of Staff": ["chief of staff", "COS"],
    "Founder / Startup": ["founding product", "early stage PM", "startup product"],
}

def get_readiness_dimensions(target_role: str) -> list:
    return ROLE_READINESS_DIMENSIONS.get(target_role, ROLE_READINESS_DIMENSIONS["default"])

def get_search_keywords(target_role: str) -> list:
    return ROLE_SEARCH_KEYWORDS.get(target_role, [target_role.lower()])
