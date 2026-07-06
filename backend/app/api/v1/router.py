from fastapi import APIRouter
from app.api.v1 import (
    users, resumes, analyses, applications,
    insights, dashboard, webhooks, billing,
    feedback, jobs, outreach, admin
)

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["Analyses"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(insights.router, prefix="/insights", tags=["Insights"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(outreach.router, prefix="/outreach", tags=["Outreach"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
