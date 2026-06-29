"""Provisioning API endpoints."""
from fastapi import APIRouter, HTTPException

from server.modules.providers.registry import ProviderRegistry
from server.modules.provisioning.schemas import (
    ProviderPlatformCreate,
    ProviderPlatformUpdate,
)
from server.modules.provisioning.services import ProviderPlatformService, ProvisioningService

router = APIRouter()


@router.post("/api/provisioning/sync")
async def trigger_sync():
    """Manually trigger provider model catalog sync."""
    changes = []
    try:
        changes = await ProvisioningService.sync_all(dry_run=False)
    finally:
        await ProviderRegistry.reload_from_db()
    summary = {"insert": 0, "disable": 0, "update": 0}
    for c in changes:
        action = c["action"].lower()
        if action in summary:
            summary[action] += 1
    return {
        "changes": changes,
        "summary": summary,
        "total": len(changes),
    }


@router.post("/api/provisioning/refresh-catalog")
async def refresh_catalog():
    """Force-refetch catalog.json from models.dev, then re-run full sync."""
    try:
        result = await ProvisioningService.refresh_catalog()
        return result
    finally:
        await ProviderRegistry.reload_from_db()


@router.get("/api/provisioning/providers")
async def list_providers():
    """List all provider platforms."""
    return await ProviderPlatformService.list()


@router.get("/api/provisioning/providers/{provider_id}")
async def get_provider(provider_id: str):
    """Get a single provider platform by ID."""
    result = await ProviderPlatformService.get(provider_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    return result


@router.post("/api/provisioning/providers")
async def create_provider(data: ProviderPlatformCreate):
    """Create a new provider platform."""
    try:
        result = await ProviderPlatformService.create(data.model_dump())
        await ProviderRegistry.reload_from_db()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/provisioning/providers/{provider_id}")
async def update_provider(provider_id: str, data: ProviderPlatformUpdate):
    """Update an existing provider platform (partial update)."""
    result = await ProviderPlatformService.update(provider_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    await ProviderRegistry.reload_from_db()
    return result


@router.delete("/api/provisioning/providers/{provider_id}")
async def delete_provider(provider_id: str):
    """Delete a provider platform. Fails with 409 if provider has active API keys."""
    result = await ProviderPlatformService.delete(provider_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    if result == "has_keys":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete '{provider_id}': "
                "has active API keys. Disable or remove keys first."
            ),
        )
    await ProviderRegistry.reload_from_db()
    return {"status": "deleted", "provider_id": provider_id}


@router.patch("/api/provisioning/providers/{provider_id}/toggle")
async def toggle_provider(provider_id: str):
    """Toggle provider enabled/disabled."""
    result = await ProviderPlatformService.toggle_enabled(provider_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    await ProviderRegistry.reload_from_db()
    return result
