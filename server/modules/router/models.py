import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from server.core.database import Base


class FallbackConfig(Base):
    __tablename__ = "fallback_config"

    model_db_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id"), nullable=False)
    pool: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class RateLimitUsage(Base):
    __tablename__ = "rate_limit_usage"

    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    key_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RateLimitCooldown(Base):
    __tablename__ = "rate_limit_cooldowns"

    platform: Mapped[str] = mapped_column(String(50), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    key_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    expires_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id: Mapped[str] = mapped_column(default=lambda: str(uuid.uuid4()), primary_key=False)  # noqa: E501
