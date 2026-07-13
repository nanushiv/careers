"""
CareerOS Backend — FastAPI Application
"""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import sentry_sdk
import logging

from app.core.config import settings
from app.core.database import init_db
from app.core.cache import init_cache
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)

if settings.SENTRY_DSN and settings.APP_ENV == "production":
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1, environment=settings.APP_ENV)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CareerOS API starting up...")
    if settings.APP_ENV == "production":
        if settings.SECRET_KEY == "change-me-in-production":
            raise RuntimeError("SECRET_KEY must be set to a secure value in production")
        if not settings.CLERK_WEBHOOK_SECRET:
            logger.warning("CLERK_WEBHOOK_SECRET is not set — Clerk webhooks will be rejected")
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.warning("RAZORPAY_WEBHOOK_SECRET is not set — Razorpay webhooks will be rejected")
    await init_db()
    await init_cache()
    _cleanup_stale_jobs()
    yield
    logger.info("CareerOS API shutting down...")


def _cleanup_stale_jobs():
    """Mark any jobs stuck in queued/processing as failed.
    Runs at startup so a Render redeploy doesn't leave users with infinite spinners."""
    try:
        from app.core.database import supabase
        result = supabase.table("analysis_jobs").update({
            "status": "failed",
            "error": "Server restarted mid-analysis. Please re-run your analysis.",
        }).in_("status", ["queued", "processing"]).execute()
        count = len(result.data) if result.data else 0
        if count:
            logger.info(f"Startup cleanup: marked {count} stale job(s) as failed")
    except Exception as e:
        logger.warning(f"Startup job cleanup failed (non-critical): {e}")


DESCRIPTION = """
## CareerOS — AI Career Intelligence & Job Hunt Operating System

AI-driven SaaS that tells tech professionals *exactly* why they're not getting hired.

### Authentication
All endpoints require a **Clerk JWT** in `Authorization: Bearer <token>`.

### Plans
| Plan | Analyses/month | Applications | Recruiter Perception |
|------|---------------|--------------|----------------------|
| Free | 5 | 10 | ❌ |
| Pro  | Unlimited | Unlimited | ✅ |

### Core Flow
1. Upload resume → `POST /v1/resumes/upload`
2. Trigger analysis → `POST /v1/analyses`
3. Poll job status via Supabase Realtime or `GET /v1/analyses`
4. View dashboard → `GET /v1/dashboard`
"""

app = FastAPI(
    title="CareerOS API",
    description=DESCRIPTION,
    version="1.0.0",
    contact={"name": "CareerOS Support", "email": "shivani27chaudhary@gmail.com"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Users", "description": "Profile and onboarding"},
        {"name": "Resumes", "description": "Upload, parse, version management"},
        {"name": "Analyses", "description": "ATS, recruiter, role fit, readiness analysis"},
        {"name": "Applications", "description": "Job application tracking and pipeline"},
        {"name": "Insights", "description": "AI-generated strategic insights"},
        {"name": "Dashboard", "description": "Aggregated dashboard data"},
        {"name": "Billing", "description": "Stripe subscription management"},
        {"name": "Webhooks", "description": "Clerk and Stripe webhooks"},
    ],
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in settings.allowed_origins_list or any(origin.endswith(".vercel.app") for origin in [origin]):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        headers=headers,
    )

app.include_router(api_router, prefix="/v1")

# Serve locally uploaded files (dev fallback when R2 is not configured)
_local_files_dir = os.path.join(os.path.dirname(__file__), "../../local_files")
os.makedirs(_local_files_dir, exist_ok=True)
app.mount("/files", StaticFiles(directory=_local_files_dir), name="local_files")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "careeros-api", "version": "1.0.0"}


@app.get("/health/db", tags=["Health"])
async def health_db():
    """Public: tests Supabase connectivity without auth."""
    from app.core.database import supabase
    try:
        resp = supabase.table("users").select("id").limit(1).execute()
        return {"db": "ok", "rows": len(resp.data or [])}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


@app.get("/dev/token", tags=["Dev"], include_in_schema=True,
         summary="[DEV ONLY] Get a fresh Clerk JWT for Swagger testing")
async def dev_get_token():
    """
    Returns a fresh Clerk JWT for the development user.
    **Only works when APP_ENV != production.**
    Use this to authorize Swagger: copy the token, click Authorize, paste it.
    """
    if settings.APP_ENV == "production":
        raise HTTPException(status_code=404, detail="Not found")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.clerk.com/v1/sessions/{settings.CLERK_DEV_SESSION_ID}/tokens",
            headers={
                "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            content=b"{}",
        )
    data = resp.json()
    token = data.get("jwt")
    if not token:
        raise HTTPException(status_code=500, detail=f"Clerk error: {data}")
    return {"token": token, "usage": f"Click 'Authorize' above → paste: Bearer {token}"}
