import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Float, Integer, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.provider_service import ProviderService
    from app.models.bid import Bid
    from app.models.booking import Booking
    from app.models.review import Review
    from app.models.favorite import Favorite


class Provider(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "providers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    business_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    trade: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    license_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_license_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Operational metrics & parameters
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    service_radius_miles: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Geographic coordinates for radius matching
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    # Aggregate performance counters (cached for fast indexing)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="provider_profile")
    services: Mapped[List["ProviderService"]] = relationship(
        "ProviderService",
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="provider",
        foreign_keys="Booking.provider_id",
    )
    received_reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="provider",
        foreign_keys="Review.provider_id",
        cascade="all, delete-orphan",
    )
    favorited_by: Mapped[List["Favorite"]] = relationship(
        "Favorite",
        back_populates="provider",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_providers_geo", "latitude", "longitude"),
        Index("ix_providers_trade_active", "trade", "is_available", "is_license_verified"),
    )
