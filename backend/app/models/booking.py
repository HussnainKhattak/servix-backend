import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Float,
    ForeignKey,
    DateTime,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import BookingStatus, EscrowStatus

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.bid import Bid
    from app.models.user import User
    from app.models.provider import Provider
    from app.models.review import Review


class Booking(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bookings"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    bid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bids.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Financial & Escrow metrics
    agreed_price: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    provider_payout: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[BookingStatus] = mapped_column(
        SQLEnum(BookingStatus, name="booking_status_enum"),
        default=BookingStatus.CONFIRMED,
        nullable=False,
        index=True,
    )
    escrow_status: Mapped[EscrowStatus] = mapped_column(
        SQLEnum(EscrowStatus, name="escrow_status_enum"),
        default=EscrowStatus.HOLDING,
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_date: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_time: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="booking")
    accepted_bid: Mapped["Bid"] = relationship("Bid", back_populates="booking")
    customer: Mapped["User"] = relationship("User", back_populates="customer_bookings", foreign_keys=[customer_id])
    provider: Mapped["Provider"] = relationship("Provider", back_populates="bookings", foreign_keys=[provider_id])
    review: Mapped[Optional["Review"]] = relationship("Review", back_populates="booking", uselist=False)

    __table_args__ = (
        Index("ix_bookings_customer_status", "customer_id", "status"),
        Index("ix_bookings_provider_status", "provider_id", "status"),
    )
