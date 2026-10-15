import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Float,
    Integer,
    ForeignKey,
    Text,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import JobStatus, UrgencyLevel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import ServiceCategory
    from app.models.bid import Bid
    from app.models.booking import Booking


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[UrgencyLevel] = mapped_column(
        SQLEnum(UrgencyLevel, name="urgency_level_enum"),
        default=UrgencyLevel.FLEXIBLE,
        nullable=False,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status_enum"),
        default=JobStatus.OPEN,
        nullable=False,
        index=True,
    )
    target_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Physical Service Location
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer: Mapped["User"] = relationship("User", back_populates="posted_jobs")
    category: Mapped["ServiceCategory"] = relationship("ServiceCategory", back_populates="jobs")
    images: Mapped[List["JobImage"]] = relationship(
        "JobImage",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    booking: Mapped[Optional["Booking"]] = relationship(
        "Booking",
        back_populates="job",
        uselist=False,
    )

    @property
    def bids_count(self) -> int:
        return len(self.bids) if self.bids else 0

    @property
    def lowest_bid(self) -> Optional[float]:
        if not self.bids:
            return None
        valid_amounts = [b.amount for b in self.bids if b.amount is not None]
        return min(valid_amounts) if valid_amounts else None

    __table_args__ = (
        Index("ix_jobs_geo_status", "latitude", "longitude", "status"),
        Index("ix_jobs_category_status", "category_id", "status"),
    )


class JobImage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_images"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="images")
