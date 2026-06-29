from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.modules.embeddings.schemas import EmbeddingOptions, EmbeddingResponse
from server.modules.keys.models import ApiKey
from server.modules.providers.models import ProviderCatalog
from server.modules.providers.registry import ProviderRegistry


class EmbeddingService:
    @staticmethod
    async def embed(
        db: AsyncSession, body: dict
    ) -> tuple[EmbeddingResponse, str, str]:
        """Returns (response, platform, model_id)."""
        model = body.get("model", "auto")
        opts = EmbeddingOptions(**body)

        if model == "auto":
            from server.modules.router.services import RouterService
            routed = await RouterService.select_fallback(db, "embed")
            if not routed:
                raise RuntimeError("No available model for embedding")
            model = routed["model_id"]
            provider = ProviderRegistry.get(routed["platform"])
            if not provider:
                raise RuntimeError(f"Provider '{routed['platform']}' not found")
            stmt = select(ApiKey).where(
                and_(ApiKey.platform == routed["platform"], ApiKey.enabled)
            ).limit(1)
            key_result = await db.execute(stmt)
            api_key_obj = key_result.scalar_one_or_none()
            if not api_key_obj:
                raise RuntimeError(f"No active API key for {routed['platform']}")
            from server.lib.crypto import decrypt
            decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)
            resp = await provider.embed(decrypted_key, opts.input, model, opts)
            return resp, routed["platform"], model

        stmt = select(ProviderCatalog).where(
            and_(ProviderCatalog.model_id == model, ProviderCatalog.enabled)
        )
        result = await db.execute(stmt)
        model_row = result.scalar_one_or_none()
        if not model_row:
            raise RuntimeError(f"Model '{model}' not found")
        provider = ProviderRegistry.get(model_row.platform)
        if not provider:
            raise RuntimeError(f"Provider '{model_row.platform}' not found")
        stmt = select(ApiKey).where(
            and_(ApiKey.platform == model_row.platform, ApiKey.enabled)
        ).limit(1)
        key_result = await db.execute(stmt)
        api_key_obj = key_result.scalar_one_or_none()
        if not api_key_obj:
            raise RuntimeError(f"No active API key for {model_row.platform}")
        from server.lib.crypto import decrypt
        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)
        resp = await provider.embed(decrypted_key, opts.input, model, opts)
        return resp, model_row.platform, model
