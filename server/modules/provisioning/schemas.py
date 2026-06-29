from datetime import datetime

from pydantic import BaseModel


class ProviderPlatformBase(BaseModel):
    id: str
    name: str
    base_url: str | None = None
    timeout_ms: int = 30000
    extra_headers: dict | None = None
    is_native: bool = False
    npm_package: str | None = None
    free_tier: bool = False
    enabled: bool = True


class ProviderPlatformCreate(ProviderPlatformBase):
    pass


class ProviderPlatformUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    timeout_ms: int | None = None
    extra_headers: dict | None = None
    is_native: bool | None = None
    npm_package: str | None = None
    free_tier: bool | None = None
    enabled: bool | None = None


class ProviderPlatformResponse(ProviderPlatformBase):
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
