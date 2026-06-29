from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.core.dependencies import verify_api_key
from server.modules.analytics.services import AnalyticsService
from server.modules.embeddings.services import EmbeddingService

router = APIRouter()


@router.post("/v1/embeddings")
async def create_embeddings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    body = await request.json()
    model = body.get("model", "auto")
    try:
        resp, platform, resolved_model = await EmbeddingService.embed(db, body)
        usage = resp.usage
        await AnalyticsService.record_request(
            db, "embed", platform, resolved_model, None,
            "success", usage.prompt_tokens, 0,
        )
        return resp
    except RuntimeError as e:
        await AnalyticsService.record_request(
            db, "embed", "unknown", model, None, "error", error=str(e),
        )
        raise HTTPException(status_code=503, detail=str(e))
