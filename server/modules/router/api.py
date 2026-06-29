from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.modules.providers.models import ProviderCatalog
from server.modules.router.models import FallbackConfig

router = APIRouter()


@router.get("/api/fallback")
async def list_fallback(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(
            FallbackConfig.id,
            FallbackConfig.model_db_id,
            FallbackConfig.pool,
            FallbackConfig.priority,
            FallbackConfig.enabled,
            ProviderCatalog.platform,
            ProviderCatalog.model_id,
            ProviderCatalog.display_name,
            ProviderCatalog.supports_tools,
        )
        .join(ProviderCatalog, FallbackConfig.model_db_id == ProviderCatalog.id)
        .order_by(FallbackConfig.pool, FallbackConfig.priority)
    )
    rows = result.all()
    return [
        {
            "id": str(r.id),
            "model_db_id": str(r.model_db_id),
            "platform": r.platform,
            "model_id": r.model_id,
            "display_name": r.display_name,
            "pool": r.pool,
            "priority": r.priority,
            "enabled": r.enabled,
            "supports_tools": r.supports_tools,
        }
        for r in rows
    ]


@router.post("/api/fallback")
async def create_fallback(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    fb = FallbackConfig(
        model_db_id=data["model_db_id"],
        pool=data["pool"],
        priority=data["priority"],
        enabled=data.get("enabled", True),
    )
    db.add(fb)
    await db.flush()
    await db.refresh(fb)
    return {"id": str(fb.id), "pool": fb.pool, "priority": fb.priority}


@router.delete("/api/fallback/{fb_id}")
async def delete_fallback(
    fb_id: str,
    db: AsyncSession = Depends(get_db),

):
    result = await db.execute(select(FallbackConfig).where(FallbackConfig.id == fb_id))
    fb = result.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="Fallback config not found")
    await db.delete(fb)
    return {"status": "deleted"}


@router.put("/api/fallback/{fb_id}")
async def update_fallback(
    fb_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),

):
    result = await db.execute(select(FallbackConfig).where(FallbackConfig.id == fb_id))
    fb = result.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="Fallback config not found")
    if "priority" in data:
        fb.priority = data["priority"]
    if "enabled" in data:
        fb.enabled = data["enabled"]
    if "pool" in data:
        fb.pool = data["pool"]
    await db.flush()
    return {"status": "updated"}
