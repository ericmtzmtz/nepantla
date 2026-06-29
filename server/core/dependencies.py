import hmac

from fastapi import Header, HTTPException, status

from server.core.config import settings


async def verify_api_key(authorization: str = Header(...)) -> str:
    """Validate unified API key from Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    if not settings.UNIFIED_API_KEY:
        return token  # No key configured — allow
    if hmac.compare_digest(token, settings.UNIFIED_API_KEY):
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )
