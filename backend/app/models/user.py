import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Enum as SQLEnum, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.technician_profile import TechnicianProfile
    from app.models.provider import Provider
    from app.models.job import Job
    from app.models.booking import Booking
    from app.models.review import Review
    from app.models.favorite import Favorite
    from app.models.notification import Notification


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", values_callable=lambda x: [e.value for e in x]),
        default=UserRole.CLIENT,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Location & address defaults
    default_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    technician_profile: Mapped[Optional["TechnicianProfile"]] = relationship(
        "TechnicianProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    provider_profile: Mapped[Optional["Provider"]] = relationship(
        "Provider",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    posted_jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="customer",
        cascade="all, delete-orphan",
        foreign_keys="Job.customer_id",
    )
    customer_bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="customer",
        foreign_keys="Booking.customer_id",
    )
    given_reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="customer",
        foreign_keys="Review.customer_id",
    )
    favorites: Mapped[List["Favorite"]] = relationship(
        "Favorite",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_users_geo", "latitude", "longitude"),
    )
