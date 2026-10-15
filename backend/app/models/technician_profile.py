import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, ForeignKey, Text, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import TechnicianTrade, AvailabilityStatus

if TYPE_CHECKING:
    from app.models.user import User


class TechnicianProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Technician Profile model linked 1:1 with User.
    Stores technician-specific details, trade categorization, pricing, 
    availability status, and aggregate rating metrics.
    """
    __tablename__ = "technician_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Trade / Specialty Category
    trade: Mapped[TechnicianTrade] = mapped_column(
        SQLEnum(TechnicianTrade, name="technician_trade_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # Professional Summary & Pricing
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    base_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Operational Availability
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        SQLEnum(AvailabilityStatus, name="availability_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=AvailabilityStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    # Performance and Rating Metrics
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Location & Service Area
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # One-to-one relationship with base User
    user: Mapped["User"] = relationship("User", back_populates="technician_profile")

    __table_args__ = (
        Index("ix_technician_profiles_geo", "latitude", "longitude"),
        Index("ix_technician_profiles_trade_status", "trade", "availability_status"),
    )
