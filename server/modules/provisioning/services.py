"""Provisioning service: sync model catalogs from providers to DB."""
import time

from sqlalchemy import select, update

from server.core.database import AsyncSessionLocal
from server.modules.providers.models import ProviderCatalog
from server.modules.provisioning.models import ProvisioningLog


class ProvisioningService:
    @staticmethod
    async def _sync_all_internal(dry_run: bool = False) -> list[dict]:
        """Internal implementation with explicit db session."""
        from server.modules.provisioning.catalog import fetch_catalog, parse_models

        changes: list[dict] = []

        async with AsyncSessionLocal() as db:
            catalog = await fetch_catalog()
            discovered_models = parse_models(catalog)
            discovered: dict[tuple[str, str], dict] = {
                (m["platform"], m["model_id"]): m for m in discovered_models
            }

            existing_result = await db.execute(select(ProviderCatalog))
            existing: dict[tuple[str, str], ProviderCatalog] = {
                (r.platform, r.model_id): r for r in existing_result.scalars().all()
            }
            to_update_keys = set(discovered.keys()) & set(existing.keys())

            for key in to_update_keys:
                info = discovered[key]
                plat, mid = key
                record = existing[key]
                changed = (
                    record.display_name != info["display_name"]
                    or record.intelligence_rank != info["intelligence_rank"]
                    or record.speed_rank != info["speed_rank"]
                    or record.size_label != info["size_label"]
                    or record.context_window != info["context_window"]
                    or record.supports_vision != info["supports_vision"]
                    or record.supports_image_gen != info["supports_image_gen"]
                    or record.supports_audio_stt != info["supports_audio_stt"]
                    or record.supports_audio_tts != info["supports_audio_tts"]
                    or record.supports_embeddings != info["supports_embeddings"]
                )
                if changed:
                    changes.append({
                        "action": "UPDATE",
                        "platform": plat,
                        "model_id": mid,
                        "details": {
                            "before": {
                                "display_name": record.display_name,
                                "intelligence_rank": record.intelligence_rank,
                                "speed_rank": record.speed_rank,
                                "size_label": record.size_label,
                                "context_window": record.context_window,
                                "supports_vision": record.supports_vision,
                                "supports_image_gen": record.supports_image_gen,
                                "supports_audio_stt": record.supports_audio_stt,
                                "supports_audio_tts": record.supports_audio_tts,
                                "supports_embeddings": record.supports_embeddings,
                            },
                            "after": info,
                        },
                    })
                    if not dry_run:
                        await db.execute(
                            update(ProviderCatalog)
                            .where(
                                ProviderCatalog.platform == plat,
                                ProviderCatalog.model_id == mid,
                            )
                            .values(**info)
                        )

            for ch in changes:
                log_entry = ProvisioningLog(
                    provider=ch["platform"],
                    model_id=ch["model_id"],
                    action=ch["action"],
                    details=str(ch.get("details", ""))[:2000],
                )
                db.add(log_entry)

            if not dry_run:
                await db.commit()

        return changes

    @staticmethod
    async def sync_providers_from_catalog(dry_run: bool = False) -> list[dict]:
        """Sync provider_platforms from models.dev catalog.json with local overrides.
        Only updates existing providers that match by ID. Does NOT insert or disable.
        """
        import logging
        logger = logging.getLogger(__name__)

        from server.modules.provisioning.catalog import (
            apply_overrides,
            fetch_catalog,
            load_overrides,
            parse_providers,
        )
        from server.modules.provisioning.models import ProviderPlatform

        changes: list[dict] = []
        catalog = await fetch_catalog()
        providers = parse_providers(catalog)
        overrides = load_overrides()
        providers = apply_overrides(providers, overrides)
        # Fix is_native for providers that got base_url from overrides
        for p in providers:
            if p.get("base_url") and p.get("is_native"):
                p["is_native"] = False

        async with AsyncSessionLocal() as db:
            existing_result = await db.execute(select(ProviderPlatform))
            existing_map = {r.id: r for r in existing_result.scalars().all()}

            catalog_ids = set()
            for p in providers:
                pid = p["id"]
                catalog_ids.add(pid)
                if pid in existing_map:
                    record = existing_map[pid]
                    # Skip base_url/is_native in change detection if catalog has no API URL
                    skip_keys = set()
                    if p.get("base_url") is None and record.base_url is not None:
                        skip_keys = {"base_url", "is_native"}
                    changed = any(
                        getattr(record, k, None) != v
                        for k, v in p.items()
                        if k != "id" and k not in skip_keys
                    )
                    if changed:
                        changes.append({"action": "UPDATE", "platform": pid, "details": p})
                        if not dry_run:
                            update_values = {k: v for k, v in p.items() if k != "id"}
                            # Don't overwrite base_url/is_native when catalog lacks API URL
                            if p.get("base_url") is None and record.base_url is not None:
                                update_values.pop("base_url", None)
                                update_values.pop("is_native", None)
                            await db.execute(
                                update(ProviderPlatform)
                                .where(ProviderPlatform.id == pid)
                                .values(**update_values)
                            )
                else:
                    logger.warning(
                        "Catalog has provider '%s' not in DB — run seed or use CRUD API",
                        pid,
                    )
                    if dry_run:
                        changes.append({
                            "action": "SKIP (not in DB)",
                            "platform": pid,
                            "details": p,
                        })

            # Warn about DB providers not in catalog
            existing_ids = set(existing_map.keys())
            for pid in existing_ids - catalog_ids:
                logger.warning("Provider '%s' in DB but not in catalog — keeping as-is", pid)
                if dry_run:
                    changes.append({"action": "KEEP (not in catalog)", "platform": pid})

            if not dry_run:
                await db.commit()

        return changes

    @staticmethod
    async def refresh_catalog() -> dict:
        """Force-refetch catalog.json, invalidate cache, re-run full sync."""
        from server.modules.provisioning.catalog import invalidate_cache

        invalidate_cache()
        provider_changes = await ProvisioningService.sync_providers_from_catalog(dry_run=False)
        model_changes = await ProvisioningService._sync_all_internal(dry_run=False)

        summary = {"inserted": 0, "disabled": 0, "updated": 0}
        for c in provider_changes + model_changes:
            action = c["action"].lower()
            if action in summary:
                summary[action] += 1

        return {
            "provider_changes": provider_changes,
            "model_changes": model_changes,
            "summary": summary,
            "total": len(provider_changes) + len(model_changes),
        }

    @staticmethod
    async def sync_all(dry_run: bool = False) -> list[dict]:
        """Public API — syncs both provider platforms and model catalog from catalog.json."""
        await ProvisioningService.sync_providers_from_catalog(dry_run=dry_run)
        return await ProvisioningService._sync_all_internal(dry_run=dry_run)

    @staticmethod
    async def probe_rate_limits(api_key: str, provider) -> dict:
        """Send a minimal chat request to probe RPM/RPD limits."""
        from server.modules.providers.schemas import ChatMessage, CompletionOptions

        limits: dict[str, int | None] = {
            "rpm": None, "rpd": None, "tpm": None, "tpd": None,
        }
        sample_messages = [ChatMessage(role="user", content="hi")]

        try:
            await provider.chat_completion(
                api_key,
                sample_messages,
                "test-probe",
                CompletionOptions(max_tokens=1),
            )
        except RuntimeError as e:
            err_msg = str(e).lower()
            if "rate limit" in err_msg or "429" in err_msg:
                limits["rpm"] = 0
        except NotImplementedError:
            pass
        except Exception:
            pass

        return limits


class ProviderPlatformService:
    """Service for reading provider platform data with in-memory cache."""

    _cache: dict[str, dict] = {}
    _cache_ttl: float = 0  # timestamp when cache expires

    @classmethod
    async def get(cls, platform: str) -> dict | None:
        """Get a single provider platform by ID, with 60s TTL cache."""
        now = time.time()
        if cls._cache and now < cls._cache_ttl and platform in cls._cache:
            return cls._cache[platform]

        # Cache miss or expired — reload all from DB
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ProviderPlatform))
            rows = result.scalars().all()
            cls._cache = {r.id: {
                "id": r.id,
                "name": r.name,
                "base_url": r.base_url,
                "timeout_ms": r.timeout_ms,
                "extra_headers": r.extra_headers,
                "is_native": r.is_native,
                "npm_package": r.npm_package,
                "free_tier": r.free_tier,
                "enabled": r.enabled,
            } for r in rows}
            cls._cache_ttl = now + 60

        return cls._cache.get(platform)

    @classmethod
    def invalidate_cache(cls):
        """Force cache refresh on next get()."""
        cls._cache = {}
        cls._cache_ttl = 0


    @classmethod
    async def list(cls) -> list[dict]:
        """List all provider platforms (populates cache)."""
        # Trigger cache population by fetching a known platform
        await cls.get("__dummy__")
        return list(cls._cache.values())

    @classmethod
    async def set_enabled(cls, platform: str, enabled: bool) -> bool:
        """Enable or disable a provider platform."""
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProviderPlatform).where(ProviderPlatform.id == platform)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.enabled = enabled
            await db.commit()
        cls.invalidate_cache()
        return True

    @classmethod
    async def set_free_tier(cls, platform: str, free_tier: bool) -> bool:
        """Manually set free_tier flag for a provider."""
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProviderPlatform).where(ProviderPlatform.id == platform)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.free_tier = free_tier
            await db.commit()
        cls.invalidate_cache()
        return True

    @classmethod
    async def create(cls, data: dict) -> dict:
        '''Create a new provider platform.'''
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            platform = ProviderPlatform(**data)
            db.add(platform)
            await db.commit()
            await db.refresh(platform)
        cls.invalidate_cache()
        return {
            "id": platform.id,
            "name": platform.name,
            "base_url": platform.base_url,
            "timeout_ms": platform.timeout_ms,
            "extra_headers": platform.extra_headers,
            "is_native": platform.is_native,
            "npm_package": platform.npm_package,
            "free_tier": platform.free_tier,
            "enabled": platform.enabled,
        }

    @classmethod
    async def update(cls, platform_id: str, data: dict) -> dict | None:
        '''Update a provider platform. Only updates provided fields.'''
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProviderPlatform).where(ProviderPlatform.id == platform_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            for key, value in data.items():
                if hasattr(row, key) and value is not None:
                    setattr(row, key, value)
            await db.commit()
            await db.refresh(row)
        cls.invalidate_cache()
        return {
            "id": row.id,
            "name": row.name,
            "base_url": row.base_url,
            "timeout_ms": row.timeout_ms,
            "extra_headers": row.extra_headers,
            "is_native": row.is_native,
            "npm_package": row.npm_package,
            "free_tier": row.free_tier,
            "enabled": row.enabled,
        }

    @classmethod
    async def delete(cls, platform_id: str):
        '''Delete a provider platform.
        Returns: True if deleted, "has_keys" if active keys exist, None if not found.
        '''
        from server.modules.keys.models import ApiKey
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            # Check for active keys
            key_result = await db.execute(
                select(ApiKey).where(ApiKey.platform == platform_id).where(ApiKey.enabled).limit(1)
            )
            if key_result.scalar_one_or_none():
                return "has_keys"

            # Find row
            result = await db.execute(
                select(ProviderPlatform).where(ProviderPlatform.id == platform_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            await db.delete(row)
            await db.commit()
        cls.invalidate_cache()
        return True

    @classmethod
    async def toggle_enabled(cls, platform_id: str) -> dict | None:
        '''Toggle the enabled flag. Returns updated row or None if not found.'''
        from server.modules.provisioning.models import ProviderPlatform

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProviderPlatform).where(ProviderPlatform.id == platform_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.enabled = not row.enabled
            await db.commit()
            await db.refresh(row)
        cls.invalidate_cache()
        return {
            "id": row.id,
            "name": row.name,
            "base_url": row.base_url,
            "timeout_ms": row.timeout_ms,
            "extra_headers": row.extra_headers,
            "is_native": row.is_native,
            "npm_package": row.npm_package,
            "free_tier": row.free_tier,
            "enabled": row.enabled,
        }
