import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.0 declarative models.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Defaults table name to snake_case of class name if not explicitly set
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name if name.endswith("s") else f"{name}s"

    def as_dict(self) -> Dict[str, Any]:
        """Convert model attributes to dictionary."""
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }


class UUIDPrimaryKeyMixin:
    """Mixin providing UUID v4 primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        sort_order=-10,
    )


class TimestampMixin:
    """Mixin providing automatic UTC timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        sort_order=101,
    )
