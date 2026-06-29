
from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from server.core.database import Base


class ProviderCatalog(Base):
    __tablename__ = "models"

    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    intelligence_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    speed_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    size_label: Mapped[str] = mapped_column(String(50), default="")
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpd_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tpd_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_token_budget: Mapped[str] = mapped_column(String(100), default="")
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_image_gen: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_audio_stt: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_audio_tts: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_embeddings: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    free_tier: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("platform", "model_id", name="uq_models_platform_model"),
    )
