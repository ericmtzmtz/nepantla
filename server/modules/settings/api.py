import secrets

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import settings as app_settings
from server.core.database import get_db
from server.modules.settings.models import Setting

router = APIRouter()


@router.get("/api/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


@router.post("/api/settings")
async def update_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    for key, value in data.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    await db.flush()
    return {"status": "updated"}


@router.get("/api/settings/api-key")
async def get_api_key(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Setting).where(Setting.key == "api_key"))
    setting = result.scalar_one_or_none()
    key = setting.value if setting else app_settings.UNIFIED_API_KEY
    host = app_settings.DB_URL.split(":")[0] if ":" in app_settings.DB_URL else "8000"
    return {"key": key, "baseUrl": f"http://localhost:{host}", "endpoint": "/v1/chat/completions"}


@router.post("/api/settings/api-key/regenerate")
async def regenerate_api_key(
    db: AsyncSession = Depends(get_db),
):
    new_key = secrets.token_hex(32)
    result = await db.execute(select(Setting).where(Setting.key == "api_key"))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = new_key
    else:
        db.add(Setting(key="api_key", value=new_key))
    await db.flush()
    return {"key": new_key}
