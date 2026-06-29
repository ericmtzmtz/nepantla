
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from server.core.database import Base


class ProvisioningLog(Base):
    __tablename__ = "provisioning_log"

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProviderPlatform(Base):
    __tablename__ = "provider_platforms"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=30000)
    extra_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_native: Mapped[bool] = mapped_column(Boolean, default=False)
    npm_package: Mapped[str | None] = mapped_column(String(100), nullable=True)
    free_tier: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

