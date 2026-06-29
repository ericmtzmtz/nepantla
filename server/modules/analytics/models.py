"""Analytics models."""
# ruff: noqa: E501
import uuid

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from server.core.database import Base


class Request(Base):
    __tablename__ = "requests"

    type: Mapped[str] = mapped_column(String(20), default="chat")
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    key_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class HourlyAgg(Base):
    __tablename__ = "hourly_agg"

    hour = mapped_column(DateTime(timezone=True), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Double, default=0.0)
