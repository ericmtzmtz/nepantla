from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import settings
from server.core.database import get_db

router = APIRouter()


@router.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    keys_result = await db.execute(
        text("SELECT platform, status, enabled FROM api_keys")
    )
    key_rows = keys_result.all()

    platforms = {}
    for row in key_rows:
        p = row.platform
        if p not in platforms:
            platforms[p] = {
                "totalKeys": 0, "healthyKeys": 0,
                "rateLimitedKeys": 0, "invalidKeys": 0, "unknownKeys": 0, "enabled": True,
            }
        platforms[p]["totalKeys"] += 1
        if row.status == "healthy":
            platforms[p]["healthyKeys"] += 1
        elif row.status == "rate_limited":
            platforms[p]["rateLimitedKeys"] += 1
        elif row.status in ("invalid", "error"):
            platforms[p]["invalidKeys"] += 1
        else:
            platforms[p]["unknownKeys"] += 1
        if not row.enabled:
            platforms[p]["enabled"] = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "database": "connected" if db_ok else "error",
        "platforms": platforms,
    }


@router.get("/health")
async def simple_health():
    return {"status": "healthy"}
