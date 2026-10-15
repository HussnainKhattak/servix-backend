import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Float,
    ForeignKey,
    Text,
    DateTime,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import BidStatus

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.provider import Provider
    from app.models.booking import Booking


class Bid(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bids"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    eta_description: Mapped[str] = mapped_column(String(100), nullable=False)
    proposed_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    warranty_terms: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    status: Mapped[BidStatus] = mapped_column(
        SQLEnum(BidStatus, name="bid_status_enum"),
        default=BidStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="bids")
    provider: Mapped["Provider"] = relationship("Provider", back_populates="bids")
    booking: Mapped[Optional["Booking"]] = relationship(
        "Booking",
        back_populates="accepted_bid",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint("job_id", "provider_id", name="uq_job_provider_bid"),
        Index("ix_bids_job_status", "job_id", "status"),
    )
