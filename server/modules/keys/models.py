from datetime import datetime as dt

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from server.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(255), default="")
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    iv: Mapped[str] = mapped_column(Text, nullable=False)
    auth_tag: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), nullable=True)
