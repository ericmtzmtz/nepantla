"""nepantla — Multi-provider LLM API proxy."""

# 0. Standard lib
import asyncio
from contextlib import asynccontextmanager

# 2. Core
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from server.core.config import settings

# 4. Import middleware
from server.middleware.error_handler import error_handler_middleware

# 1. Import models to register with Base.metadata (for Alembic)
from server.models import *  # noqa: F401, F403
from server.modules.analytics.api import router as analytics_router
from server.modules.embeddings.api import router as embeddings_router
from server.modules.health.api import router as health_router
from server.modules.keys.api import router as keys_router
from server.modules.models_view.api import router as models_router
from server.modules.providers.registry import ProviderRegistry
from server.modules.provisioning.api import router as provisioning_router

# 3. Import routers
from server.modules.proxy.api import router as proxy_router
from server.modules.router.api import router as fallback_router
from server.modules.settings.api import router as settings_router


# 7. Lifespan handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start analytics buffer worker + schedule crons
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: I001

    from server.modules.analytics.services import AnalyticsService

    scheduler = AsyncIOScheduler()
    scheduler.add_job(AnalyticsService.aggregate_hourly, "cron", hour="*", id="agg_hourly")
    scheduler.add_job(AnalyticsService.cleanup_old_requests, "cron", hour="3", id="cleanup_daily")

    from server.modules.provisioning.services import ProvisioningService
    scheduler.add_job(
        ProvisioningService.sync_all, "cron",
        hour="*/6", id="provisioning_sync",
        kwargs={"dry_run": True},
    )

    scheduler.start()

    # Load providers from DB (auto-discovered OpenAI-compatible providers)
    await ProviderRegistry.load_from_db()

    AnalyticsService.start()

    # Warmup: make a local request so Windows TCP stack is pre-warmed
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.get(f"http://127.0.0.1:{settings.PORT}/")
    except Exception:
        pass

    yield
    # Shutdown: cancel analytics worker + scheduler
    scheduler.shutdown(wait=False)
    if AnalyticsService._worker_task:
        AnalyticsService._worker_task.cancel()
        try:
            await AnalyticsService._worker_task
        except asyncio.CancelledError:
            pass


# 5. Create app
app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 6. Add middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(BaseHTTPMiddleware, dispatch=error_handler_middleware)

# Health check
@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.VERSION, "status": "ok"}

# 8. Register routers
app.include_router(proxy_router)
# /v1/chat/completions, /v1/images/generations, /v1/audio/*
app.include_router(keys_router)            # /api/keys
app.include_router(fallback_router)        # /api/fallback
app.include_router(health_router)          # /api/health, /health
app.include_router(settings_router)        # /api/settings
app.include_router(analytics_router)       # /api/analytics/*
app.include_router(embeddings_router)     # /v1/embeddings
app.include_router(models_router)          # /api/models, /v1/models
app.include_router(provisioning_router)    # /api/provisioning/sync


# 9. Entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
