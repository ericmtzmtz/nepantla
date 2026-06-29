from fastapi import APIRouter, Depends
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.modules.keys.models import ApiKey
from server.modules.providers.models import ProviderCatalog

router = APIRouter()


@router.get("/api/models")
async def list_models(
    db: AsyncSession = Depends(get_db),
):
    has_key_subq = exists(
        select(ApiKey.platform).where(
            ApiKey.enabled,
            ApiKey.platform == ProviderCatalog.platform,
        )
    ).correlate(ProviderCatalog).label("has_key")

    result = await db.execute(
        select(ProviderCatalog, has_key_subq)
        .order_by(ProviderCatalog.platform, ProviderCatalog.intelligence_rank.desc())
    )
    rows = result.all()
    return [
        {
            "id": str(m.id),
            "platform": m.platform,
            "model_id": m.model_id,
            "display_name": m.display_name,
            "enabled": m.enabled,
            "intelligence_rank": m.intelligence_rank,
            "speed_rank": m.speed_rank,
            "size_label": m.size_label,
            "context_window": m.context_window,
            "supports_vision": m.supports_vision,
            "supports_image_gen": m.supports_image_gen,
            "supports_audio_stt": m.supports_audio_stt,
            "supports_audio_tts": m.supports_audio_tts,
            "supports_embeddings": m.supports_embeddings,
            "supports_tools": m.supports_tools,
            "has_key": has_key,
            "free_tier": getattr(m, 'free_tier', False),
        }
        for m, has_key in rows
    ]


@router.get("/v1/models")
async def list_models_v1(db: AsyncSession = Depends(get_db)):
    """OpenAI-compatible models endpoint."""
    result = await db.execute(
        select(ProviderCatalog).where(ProviderCatalog.enabled)
    )
    models = result.scalars().all()
    return {
        "object": "list",
        "data": [
            {
                "id": m.model_id,
                "object": "model",
                "created": int(m.created_at.timestamp()) if m.created_at else 0,
                "owned_by": m.platform,
            }
            for m in models
        ],
    }
