import redis.asyncio as aioredis
import json
import hashlib
import logging
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: Optional[aioredis.Redis] = None


async def init_cache():
    global redis_client
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        logger.info("✅ Redis cache connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable, running without cache: {e}")
        redis_client = None


def make_cache_key(*parts: str) -> str:
    """Create a deterministic cache key from string parts."""
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


async def cache_get(key: str) -> Optional[Any]:
    if not redis_client:
        return None
    try:
        value = await redis_client.get(f"careeros:{key}")
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    if not redis_client:
        return False
    try:
        await redis_client.setex(
            f"careeros:{key}",
            ttl,
            json.dumps(value, default=str),
        )
        return True
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    if not redis_client:
        return False
    try:
        await redis_client.delete(f"careeros:{key}")
        return True
    except Exception as e:
        logger.warning(f"Cache delete error: {e}")
        return False


class CacheManager:
    """Higher-level cache manager with key namespacing."""

    TTLS = {
        "ats_analysis": 86400,        # 24h — resumes don't change often
        "role_fit": 604800,           # 7d  — embedding similarity is stable
        "recruiter_perception": 172800, # 48h — needs some freshness
        "interview_questions": 86400, # 24h
        "user_dashboard": 300,        # 5min — near-realtime dashboard
        "user_insights": 3600,        # 1h
        "embedding": 2592000,         # 30d — embeddings are deterministic
    }

    async def get_analysis(self, resume_id: str, jd_id: str, analysis_type: str):
        key = make_cache_key(resume_id, jd_id or "no_jd", analysis_type)
        return await cache_get(key)

    async def set_analysis(self, resume_id: str, jd_id: str, analysis_type: str, data: dict):
        key = make_cache_key(resume_id, jd_id or "no_jd", analysis_type)
        ttl = self.TTLS.get(analysis_type, 3600)
        return await cache_set(key, data, ttl)

    async def invalidate_resume(self, resume_id: str):
        """Called when a resume is updated — all its analyses become stale."""
        # In production, track cache keys per resume in Redis sets
        pass


cache_manager = CacheManager()
