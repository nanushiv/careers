"""
Resumes API — file upload, version management, parse trigger.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import tempfile
import os
import logging

from app.core.security import get_current_user
from app.core.database import supabase
from app.core.config import is_admin, settings
from app.services.resume.parser import resume_parser

logger = logging.getLogger(__name__)
router = APIRouter()


def api_response(data=None, error=None):
    if error:
        return {"success": False, "error": error}
    return {"success": True, "data": data}


def get_user_id(current_user: dict) -> str:
    resp = supabase.table("users").select("id, plan").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    return resp.data[0]["id"]


@router.post("/upload")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    version_label: str = Form(default="Default"),
    current_user: dict = Depends(get_current_user),
):
    """Upload a resume file. Stores in R2, parses in background."""
    # Validate file type
    allowed_types = ["application/pdf",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    file_size = 0
    content = await file.read()
    file_size = len(content) // 1024  # KB

    if file_size > 10240:  # 10MB
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    user_id = get_user_id(current_user)

    # Determine file type
    file_ext = file.filename.split(".")[-1].lower() if file.filename else "pdf"
    file_type = "pdf" if file_ext == "pdf" else "docx"

    # Generate storage path
    file_key = f"{user_id}/{uuid.uuid4()}.{file_ext}"

    # Upload to Cloudflare R2 (stub — replace with actual R2 client)
    file_url = await upload_to_r2(content, file_key, file.content_type)

    # Create DB record
    resume_record = {
        "user_id": user_id,
        "file_name": file.filename or f"resume.{file_ext}",
        "file_url": file_url,
        "file_size_kb": file_size,
        "file_type": file_type,
        "version_label": version_label,
        "parse_status": "pending",
        "is_primary": False,
    }

    # If this is the first resume, make it primary
    existing = supabase.table("resumes").select("id").eq(
        "user_id", user_id
    ).is_("deleted_at", "null").execute()
    if not existing.data:
        resume_record["is_primary"] = True

    resp = supabase.table("resumes").insert(resume_record).execute()

    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create resume record")

    resume = resp.data[0]

    # Parse in background
    background_tasks.add_task(
        parse_resume_background,
        resume_id=resume["id"],
        file_content=content,
        file_type=file_type,
    )

    return api_response(data=resume)


@router.get("")
async def list_resumes(current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    resp = supabase.table("resumes").select("*").eq(
        "user_id", user_id
    ).is_("deleted_at", "null").order("created_at", desc=True).execute()
    return api_response(data=resp.data)


@router.get("/{resume_id}")
async def get_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    resp = supabase.table("resumes").select("*").eq(
        "id", resume_id
    ).eq("user_id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Resume not found")
    return api_response(data=resp.data[0])


@router.put("/{resume_id}")
async def update_resume(
    resume_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    # If setting primary, unset all others first
    if data.get("is_primary"):
        supabase.table("resumes").update({"is_primary": False}).eq(
            "user_id", user_id
        ).execute()

    resp = supabase.table("resumes").update(data).eq(
        "id", resume_id
    ).eq("user_id", user_id).execute()

    return api_response(data=resp.data[0] if resp.data else {})


@router.post("/{resume_id}/rewrite")
async def trigger_rewrite(
    resume_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Trigger AI resume rewrite. Pro-only. Polls via resume_analyses with analysis_type=rewrite."""
    user_resp = supabase.table("users").select("id, plan, email").eq(
        "clerk_id", current_user["clerk_id"]
    ).execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_resp.data[0]



    resume_resp = supabase.table("resumes").select("*").eq(
        "id", resume_id
    ).eq("user_id", user["id"]).execute()
    if not resume_resp.data:
        raise HTTPException(status_code=404, detail="Resume not found")
    resume = resume_resp.data[0]
    if resume.get("parse_status") != "completed":
        raise HTTPException(status_code=400, detail="Resume not yet parsed")

    analyses_resp = supabase.table("resume_analyses").select("*").eq(
        "resume_id", resume_id
    ).execute()
    analyses = analyses_resp.data or []

    # Create a placeholder record so frontend can poll immediately
    record_resp = supabase.table("resume_analyses").insert({
        "user_id": user["id"],
        "resume_id": resume_id,
        "analysis_type": "rewrite",
        "rewrite_status": "processing",
    }).execute()
    record_id = record_resp.data[0]["id"] if record_resp.data else None

    background_tasks.add_task(
        run_rewrite_background,
        resume=resume,
        analyses=analyses,
        user_id=user["id"],
        record_id=record_id,
    )

    return api_response(data={"job_id": record_id, "status": "queued", "estimated_seconds": 30})


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    from datetime import datetime
    user_id = get_user_id(current_user)
    supabase.table("resumes").update({"deleted_at": datetime.utcnow().isoformat()}).eq(
        "id", resume_id
    ).eq("user_id", user_id).execute()
    return api_response(data={"deleted": True})


# ── Background Tasks ──────────────────────────────────────────────────────────

async def parse_resume_background(resume_id: str, file_content: bytes, file_type: str):
    """Parse uploaded resume and store raw text + structured data."""
    try:
        supabase.table("resumes").update({"parse_status": "processing"}).eq(
            "id", resume_id
        ).execute()

        # Write to temp file for parser
        with tempfile.NamedTemporaryFile(suffix=f".{file_type}", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            result = resume_parser.parse(tmp_path, file_type)
        finally:
            os.unlink(tmp_path)

        if result.error:
            supabase.table("resumes").update({
                "parse_status": "failed",
                "parse_error": result.error,
            }).eq("id", resume_id).execute()
            return

        # Generate embedding (optional — skip if unavailable)
        embedding = None
        try:
            from app.ai.llm_client import llm_client
            embedding = await llm_client.embed(result.raw_text[:8000])
        except Exception as emb_err:
            logger.warning(f"Embedding skipped: {emb_err}")

        update_data = {
            "parse_status": "completed",
            "raw_text": result.raw_text,
            "structured_data": result.sections,
        }
        if embedding:
            update_data["embedding"] = embedding

        supabase.table("resumes").update(update_data).eq("id", resume_id).execute()

        logger.info(f"Resume parsed successfully: {resume_id}")

    except Exception as e:
        logger.error(f"Resume parse background task failed: {e}")
        supabase.table("resumes").update({
            "parse_status": "failed",
            "parse_error": str(e),
        }).eq("id", resume_id).execute()


async def run_rewrite_background(resume: dict, analyses: list, user_id: str, record_id: str):
    """Background task: runs AI rewrite, uploads DOCX to R2, updates resume_analyses record."""
    from app.services.resume.rewriter import resume_rewriter
    try:
        result = await resume_rewriter.rewrite(resume, analyses, user_id)

        if result.error:
            logger.error(f"Rewrite failed for record {record_id}: {result.error}")
            supabase.table("resume_analyses").update({
                "rewrite_status": "failed",
            }).eq("id", record_id).execute()
            return

        update_data = {
            "rewrite_status": "completed",
            "improved_resume_url": result.docx_url,
            "model_used": result.model_used,
            "tokens_used": result.tokens_used,
            "cost_usd": result.cost_usd,
        }
        if result.pdf_url:
            update_data["improved_pdf_url"] = result.pdf_url
        if result.projected_ats_score > 0:
            update_data["overall_score"] = result.projected_ats_score
        supabase.table("resume_analyses").update(update_data).eq("id", record_id).execute()

        logger.info(f"Rewrite completed for record {record_id}: DOCX={result.docx_url} PDF={result.pdf_url}")

    except Exception as e:
        logger.error(f"Rewrite background task crashed: {e}")
        supabase.table("resume_analyses").update({
            "rewrite_status": "failed",
        }).eq("id", record_id).execute()


async def upload_to_r2(content: bytes, key: str, content_type: str) -> str:
    """Upload file — R2 if configured, else Supabase Storage. Returns public URL."""
    from app.core.config import settings

    # R2 (if configured)
    if settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            )
            s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
            return f"{settings.R2_PUBLIC_URL}/{key}"
        except Exception as e:
            logger.warning(f"R2 upload failed, falling back to Supabase Storage: {e}")

    # Supabase Storage fallback (persistent, no extra config needed)
    try:
        bucket = "improved-resumes"
        try:
            supabase.storage.create_bucket(bucket, options={"public": True})
        except Exception:
            pass  # bucket already exists
        supabase.storage.from_(bucket).upload(
            path=key,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return supabase.storage.from_(bucket).get_public_url(key)
    except Exception as e:
        logger.error(f"Supabase Storage upload failed: {e}")
        raise RuntimeError(f"File upload failed: {e}")
