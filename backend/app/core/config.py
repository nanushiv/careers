from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import json


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:3000"  # Comma-separated or single URL
    FRONTEND_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"

    @property
    def allowed_origins_list(self) -> List[str]:
        v = self.ALLOWED_ORIGINS.strip()
        if v.startswith("["):
            return json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]

    # Database
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str

    # Auth
    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_DEV_SESSION_ID: str = ""  # Dev only: session ID for /dev/token endpoint

    # Cache
    REDIS_URL: str = "redis://localhost:6379"

    # Storage
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "careeros-resumes"
    R2_PUBLIC_URL: str = ""

    # AI
    GEMINI_API_KEY: str
    OPENROUTER_API_KEY: str = ""
    EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Email
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "onboarding@resend.dev"
    NOTIFY_EMAIL: str = "shivani27chaudhary@gmail.com"

    # Payments — Razorpay (supports UPI, cards, net banking, wallets — India + global)
    RAZORPAY_KEY_ID: str = ""            # rzp_test_... or rzp_live_...
    RAZORPAY_KEY_SECRET: str = ""        # from Razorpay dashboard
    RAZORPAY_PLAN_ID: str = ""           # plan_... (₹999/month INR)
    RAZORPAY_WEBHOOK_SECRET: str = ""    # from Razorpay dashboard → Webhooks

    # Job sources
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    # Admin
    ADMIN_EMAILS: str = "shivani27chaudhary@gmail.com"
    ADMIN_CRON_SECRET: str = ""   # Set on Render; used by cron-job.org to trigger scheduled tasks
    BYPASS_PRO_GATE: bool = False

    # Analytics
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://app.posthog.com"

    # Sentry
    SENTRY_DSN: str = ""

    # Rate limits
    RATE_LIMIT_FREE_PER_MINUTE: int = 20
    RATE_LIMIT_PRO_PER_MINUTE: int = 100

    # AI Cost budgets (USD/month)
    AI_BUDGET_FREE_MONTHLY_USD: float = 0.15
    AI_BUDGET_PRO_MONTHLY_USD: float = 2.00

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def is_admin(email: str = "") -> bool:
    """Return True if pro gate should be bypassed (env flag or admin email)."""
    if settings.BYPASS_PRO_GATE:
        return True
    admins = [e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]
    return bool(email) and email.lower() in admins
