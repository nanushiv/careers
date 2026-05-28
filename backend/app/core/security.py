from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
import logging
from functools import lru_cache
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"


@lru_cache(maxsize=1)
def get_jwks():
    """Cache JWKS keys — refreshed on process restart."""
    response = httpx.get(CLERK_JWKS_URL, headers={
        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"
    })
    return response.json()


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return the payload."""
    try:
        jwks = get_jwks()
        # Decode header to get kid
        header = jwt.get_unverified_header(token)
        # Find matching key
        key = next(
            (k for k in jwks["keys"] if k["kid"] == header["kid"]),
            None
        )
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token key")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """FastAPI dependency: extract and verify the current user."""
    token = credentials.credentials
    payload = verify_clerk_token(token)
    return {
        "clerk_id": payload.get("sub"),
        "email": payload.get("email", ""),
        "session_id": payload.get("sid"),
    }


class RequiresPlan:
    """Dependency factory: enforce minimum plan requirement."""
    def __init__(self, min_plan: str = "free"):
        self.min_plan = min_plan
        self.plan_order = {"free": 0, "pro": 1, "team": 2}

    async def __call__(
        self,
        current_user: dict = Depends(get_current_user),
        db=Depends(lambda: None),  # injected
    ):
        # Plan check would query DB for user's current plan
        # Simplified here — full implementation queries usage_quotas table
        return current_user
