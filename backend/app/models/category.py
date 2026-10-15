from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.provider_service import ProviderService
    from app.models.job import Job


class ServiceCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "service_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    icon: Mapped[str] = mapped_column(String(100), default="🔧", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Benchmark pricing estimates
    avg_price_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_price_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    provider_services: Mapped[List["ProviderService"]] = relationship(
        "ProviderService",
        back_populates="category",
        cascade="all, delete-orphan",
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="category",
    )
