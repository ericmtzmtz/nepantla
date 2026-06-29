from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.lib.crypto import decrypt as lib_decrypt
from server.lib.crypto import encrypt, mask_key
from server.modules.keys.models import ApiKey
from server.modules.keys.services import KeysService

router = APIRouter()


@router.get("/api/keys")
async def list_keys(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiKey).order_by(ApiKey.platform))
    keys = result.scalars().all()
    out = []
    for k in keys:
        masked = "****"
        try:
            real = lib_decrypt(k.encrypted_key, k.iv, k.auth_tag)
            masked = mask_key(real)
        except Exception:
            masked = "[decrypt failed]"
        out.append({
            "id": str(k.id),
            "platform": k.platform,
            "label": k.label,
            "maskedKey": masked,
            "status": k.status,
            "enabled": k.enabled,
            "createdAt": str(k.created_at),
            "lastCheckedAt": str(k.last_checked_at) if k.last_checked_at else None,
        })
    return out


@router.post("/api/keys")
async def create_key(
    data: dict,
    db: AsyncSession = Depends(get_db),

):
    platform = data.get("platform", "")
    raw_key = data.get("key", "")
    label = data.get("label", "")
    if not platform or not raw_key:
        raise HTTPException(status_code=400, detail="platform and key are required")
    ct, iv, tag = encrypt(raw_key)
    key = ApiKey(
        platform=platform,
        label=label,
        encrypted_key=ct,
        iv=iv,
        auth_tag=tag,
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)
    # Best-effort validation — sets healthy/invalid/error
    await KeysService.validate_key(db, str(key.id))
    await db.refresh(key)
    return {
        "id": str(key.id),
        "platform": key.platform,
        "label": key.label,
        "status": key.status,
    }


@router.post("/api/keys/validate-all")
async def validate_all_keys(
    db: AsyncSession = Depends(get_db),
):
    counts = await KeysService.validate_all(db)
    return counts


@router.post("/api/keys/{key_id}/validate")
async def validate_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
):
    key = await KeysService.validate_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return {
        "id": str(key.id),
        "platform": key.platform,
        "status": key.status,
        "lastCheckedAt": str(key.last_checked_at) if key.last_checked_at else None,
    }


@router.delete("/api/keys/{key_id}")
async def delete_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),

):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    return {"status": "deleted"}


@router.patch("/api/keys/{key_id}")
async def update_key(
    key_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),

):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    if "label" in data:
        key.label = data["label"]
    if "enabled" in data:
        key.enabled = data["enabled"]
    await db.flush()
    return {"status": "updated"}


@router.patch("/api/keys/platform/{platform}")
async def toggle_platform(
    platform: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiKey).where(ApiKey.platform == platform))
    keys = result.scalars().all()
    enabled = data.get("enabled", True)
    for k in keys:
        k.enabled = enabled
    await db.flush()
    return {"status": "updated", "updated_keys": len(keys)}
