"""Provider registry — native providers + lazy-load from provider_platforms DB."""
import logging

from server.modules.providers.base import BaseProvider
from server.modules.providers.cloudflare import CloudflareProvider
from server.modules.providers.cohere import CohereProvider
from server.modules.providers.google import GoogleProvider
from server.modules.providers.openai_compat import GenericOpenAIProvider
from server.modules.providers.stability import StabilityAIProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    _providers: dict[str, BaseProvider] = {}
    _loaded_from_db: bool = False

    @classmethod
    def register(cls, provider: BaseProvider) -> None:
        cls._providers[provider.platform] = provider

    @classmethod
    async def load_from_db(cls):
        """Load OpenAI-compatible providers from provider_platforms DB table."""
        if cls._loaded_from_db:
            return
        try:
            from sqlalchemy import select

            from server.core.database import AsyncSessionLocal
            from server.modules.provisioning.models import ProviderPlatform

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ProviderPlatform).where(ProviderPlatform.enabled)
                )
                for row in result.scalars().all():
                    if row.id in cls._providers:
                        continue  # Don't override native providers
                    if row.is_native:
                        continue  # Native providers need explicit registration
                    if not row.base_url:
                        continue
                    cls._providers[row.id] = GenericOpenAIProvider(
                        platform=row.id,
                        base_url=row.base_url,
                        name=row.name,
                        timeout_ms=row.timeout_ms,
                        extra_headers=row.extra_headers or {},
                    )
            cls._loaded_from_db = True
            non_native = sum(
                1 for p in cls._providers.values()
                if isinstance(p, GenericOpenAIProvider)
            )
            if non_native:
                logger.info("load_from_db loaded %d generic providers", non_native)
        except Exception as e:
            logger.warning("load_from_db failed: %s", e)

    @classmethod
    async def reload_from_db(cls):
        """Force-reload all OpenAI-compatible providers from provider_platforms DB.

        Removes existing GenericOpenAIProvider entries and re-loads from DB.
        Native providers are never removed.
        """
        # Remove existing GenericOpenAIProvider entries (keep native)
        to_remove = [k for k, v in cls._providers.items()
                     if isinstance(v, GenericOpenAIProvider)]
        for k in to_remove:
            del cls._providers[k]
        cls._loaded_from_db = False
        await cls.load_from_db()

    @classmethod
    def get(cls, platform: str) -> BaseProvider | None:
        return cls._providers.get(platform)

    @classmethod
    def list_platforms(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def all(cls) -> list[BaseProvider]:
        return list(cls._providers.values())


# Register native providers (always present)
ProviderRegistry.register(GoogleProvider())
ProviderRegistry.register(CohereProvider())
ProviderRegistry.register(CloudflareProvider())
ProviderRegistry.register(StabilityAIProvider())
