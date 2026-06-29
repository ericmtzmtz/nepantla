"""Key validation service."""

from datetime import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.lib.crypto import decrypt as lib_decrypt
from server.modules.keys.models import ApiKey
from server.modules.providers.registry import ProviderRegistry


class KeysService:

    @staticmethod
    async def validate_key(db: AsyncSession, key_id: str) -> ApiKey | None:
        """Validate a single API key and update its status in DB."""
        result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
        key = result.scalar_one_or_none()
        if not key:
            return None
        return await KeysService._do_validate(db, key)

    @staticmethod
    async def validate_all(db: AsyncSession) -> dict:
        """Validate all API keys. Returns summary counts."""
        result = await db.execute(select(ApiKey))
        keys = result.scalars().all()
        counts = {"total": len(keys), "healthy": 0, "invalid": 0, "error": 0}
        for key in keys:
            await KeysService._do_validate(db, key)
            if key.status == "healthy":
                counts["healthy"] += 1
            elif key.status == "invalid":
                counts["invalid"] += 1
            else:
                counts["error"] += 1
        await db.commit()
        return counts

    @staticmethod
    async def _do_validate(db: AsyncSession, key: ApiKey) -> ApiKey:
        """Internal: run provider's validate_key and update status."""
        provider = ProviderRegistry.get(key.platform)
        if not provider:
            key.status = "error"
            key.last_checked_at = dt.now()
            return key

        try:
            raw_key = lib_decrypt(key.encrypted_key, key.iv, key.auth_tag)
            is_valid = await provider.validate_key(raw_key)
            key.status = "healthy" if is_valid else "invalid"
        except Exception:
            key.status = "error"

        key.last_checked_at = dt.now()
        return key
