import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import settings
from server.modules.analytics.services import AnalyticsService
from server.modules.keys.models import ApiKey
from server.modules.providers.models import ProviderCatalog
from server.modules.providers.registry import ProviderRegistry
from server.modules.router.models import FallbackConfig, RateLimitCooldown, RateLimitUsage


class RouterService:
    # ponytail: in-memory sticky sessions; global dict, per-account locks if throughput matters
    _sticky_sessions: dict[str, tuple[str, float]] = {}  # key -> (model_id, expiry)

    @staticmethod
    async def select_fallback(
        db: AsyncSession, pool: str, messages_hash: str = ""
    ) -> dict | None:
        """Select best model for a given pool using fallback chain."""
        # Check sticky session first — return full route info, not just model_id
        sticky_key = f"{pool}:{messages_hash}" if messages_hash else ""
        if sticky_key and sticky_key in RouterService._sticky_sessions:
            model_id, expiry = RouterService._sticky_sessions[sticky_key]
            if time.time() < expiry:
                model_row = await db.execute(
                    select(ProviderCatalog).where(ProviderCatalog.model_id == model_id).limit(1)
                )
                model = model_row.scalar_one_or_none()
                if model and (provider := ProviderRegistry.get(model.platform)):
                    key_result = await db.execute(
                        select(ApiKey)
                        .where(ApiKey.platform == model.platform)
                        .where(ApiKey.enabled)
                        .limit(1)
                    )
                    api_key = key_result.scalar_one_or_none()
                    if api_key:
                        return {
                            "platform": model.platform, "model_id": model_id,
                            "provider": provider, "api_key": api_key, "sticky": True,
                        }
                # Stale sticky — clear it and fall through
                RouterService._sticky_sessions.pop(sticky_key, None)

        # Get fallback chain ordered by priority
        # For CHAT_TOOLS pool, only include models that support tools
        if pool == "chat_tools":
            result = await db.execute(
                select(FallbackConfig, ProviderCatalog)
                .join(ProviderCatalog, FallbackConfig.model_db_id == ProviderCatalog.id)
                .where(FallbackConfig.pool == pool)
                .where(FallbackConfig.enabled)
                .where(ProviderCatalog.enabled)
                .where(ProviderCatalog.supports_tools == True)
                .order_by(FallbackConfig.priority)
            )
        else:
            result = await db.execute(
                select(FallbackConfig, ProviderCatalog)
                .join(ProviderCatalog, FallbackConfig.model_db_id == ProviderCatalog.id)
                .where(FallbackConfig.pool == pool)
                .where(FallbackConfig.enabled)
                .where(ProviderCatalog.enabled)
                .order_by(FallbackConfig.priority)
            )
        rows = result.all()

        for fb, model in rows:
            provider = ProviderRegistry.get(model.platform)
            if not provider:
                continue

            # Check cooldown
            cooldown = await db.execute(
                select(RateLimitCooldown)
                .where(RateLimitCooldown.platform == model.platform)
                .where(RateLimitCooldown.model_id == model.model_id)
            )
            if cooldown.scalar_one_or_none():
                continue

            # Find a healthy key
            key_result = await db.execute(
                select(ApiKey)
                .where(ApiKey.platform == model.platform)
                .where(ApiKey.enabled)
                .where(ApiKey.status.in_(["healthy", "unknown"]))
                .limit(1)
            )
            api_key = key_result.scalar_one_or_none()
            if not api_key:
                continue

            # Check rate limits
            can_request = await RouterService._check_rate_limit(
                db, model.platform, model.model_id, api_key.id,
                model.rpm_limit, model.rpd_limit,
                model.tpm_limit, model.tpd_limit,
            )
            if not can_request:
                continue

            # Sticky session
            if sticky_key:
                RouterService._sticky_sessions[sticky_key] = (
                    model.model_id,
                    time.time() + settings.STICKY_SESSION_TTL_MINUTES * 60,
                )
                # Cleanup if too many
                if len(RouterService._sticky_sessions) > 500:
                    now = time.time()
                    RouterService._sticky_sessions = {
                        k: v for k, v in RouterService._sticky_sessions.items()
                        if v[1] > now
                    }

            return {
                "platform": model.platform,
                "model_id": model.model_id,
                "provider": provider,
                "api_key": api_key,
                "sticky": False,
            }

        return None

    @staticmethod
    async def _check_rate_limit(
        db: AsyncSession, platform: str, model_id: str,
        key_id: uuid.UUID, rpm: int | None, rpd: int | None,
        tpm: int | None, tpd: int | None,
    ) -> bool:
        now_ms = int(time.time() * 1000)

        if rpm:
            minute_ago = now_ms - 60000
            result = await db.execute(
                select(RateLimitUsage)
                .where(RateLimitUsage.platform == platform)
                .where(RateLimitUsage.model_id == model_id)
                .where(RateLimitUsage.key_id == key_id)
                .where(RateLimitUsage.kind == "request")
                .where(RateLimitUsage.created_at_ms >= minute_ago)
            )
            if len(result.all()) >= rpm:
                return False

        if rpd:
            day_ago = now_ms - 86400000
            result = await db.execute(
                select(RateLimitUsage)
                .where(RateLimitUsage.platform == platform)
                .where(RateLimitUsage.model_id == model_id)
                .where(RateLimitUsage.key_id == key_id)
                .where(RateLimitUsage.kind == "request")
                .where(RateLimitUsage.created_at_ms >= day_ago)
            )
            if len(result.all()) >= rpd:
                return False

        return True

    @staticmethod
    async def record_request(
        db: AsyncSession, platform: str, model_id: str,
        key_id: uuid.UUID, input_tokens: int, output_tokens: int,
        success: bool = True,
    ) -> None:
        now_ms = int(time.time() * 1000)

        db.add(RateLimitUsage(
            platform=platform, model_id=model_id, key_id=key_id,
            kind="request", tokens=0, created_at_ms=now_ms,
        ))
        db.add(RateLimitUsage(
            platform=platform, model_id=model_id, key_id=key_id,
            kind="tokens", tokens=input_tokens + output_tokens, created_at_ms=now_ms,
        ))

    @staticmethod
    async def set_cooldown(
        db: AsyncSession, platform: str, model_id: str,
        key_id: uuid.UUID, penalty: int = 3,
    ) -> None:
        expires_at_ms = int(time.time() * 1000) + penalty * 60000
        existing = await db.execute(
            select(RateLimitCooldown)
            .where(RateLimitCooldown.platform == platform)
            .where(RateLimitCooldown.model_id == model_id)
            .where(RateLimitCooldown.key_id == key_id)
        )
        cd = existing.scalar_one_or_none()
        if cd:
            cd.expires_at_ms = max(cd.expires_at_ms, expires_at_ms)
        else:
            db.add(RateLimitCooldown(
                platform=platform, model_id=model_id, key_id=key_id,
                expires_at_ms=expires_at_ms,
            ))
        await AnalyticsService.record_request(
            db, "rate_limit", platform, model_id, key_id,
            "error", error="rate_limited",
        )
