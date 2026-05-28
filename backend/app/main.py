"""
CareerOS Backend — FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
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
    await init_db()
    await init_cache()
    yield
    logger.info("CareerOS API shutting down...")


DESCRIPTION = """
## CareerOS — AI Career Intelligence & Job Hunt Operating System

AI-driven SaaS that tells tech professionals *exactly* why they're not getting hired.

### Authentication
All endpoints require a **Clerk JWT** in `Authorization: Bearer <token>`.

### Plans
| Plan | Analyses/month | Applications | Recruiter Perception |
|------|---------------|--------------|----------------------|
| Free | 3 | 10 | ❌ |
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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}})

app.include_router(api_router, prefix="/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "careeros-api", "version": "1.0.0"}


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
            headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
        )
    data = resp.json()
    token = data.get("jwt")
    if not token:
        raise HTTPException(status_code=500, detail=f"Clerk error: {data}")
    return {"token": token, "usage": f"Click 'Authorize' above → paste: Bearer {token}"}
