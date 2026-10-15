import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.enums import BookingStatus
from app.schemas.booking import BookingCreate
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking, BookingCreate, BookingCreate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Booking, session)

    async def get_by_id_with_relations(self, id: uuid.UUID) -> Optional[Booking]:
        """Fetch booking with job, customer, provider, and review eagerly loaded."""
        result = await self.session.execute(
            select(Booking)
            .where(Booking.id == id)
            .options(
                selectinload(Booking.job),
                selectinload(Booking.customer),
                selectinload(Booking.provider).selectinload(Provider.user),
                selectinload(Booking.accepted_bid),
                selectinload(Booking.review),
            )
        )
        return result.scalars().first()

    async def get_by_customer(
        self, customer_id: uuid.UUID, status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """Fetch bookings for customer."""
        query = (
            select(Booking)
            .where(Booking.customer_id == customer_id)
            .options(
                selectinload(Booking.job),
                selectinload(Booking.provider).selectinload(Provider.user),
            )
            .order_by(Booking.created_at.desc())
        )
        if status:
            query = query.where(Booking.status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_provider(
        self, provider_id: uuid.UUID, status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """Fetch bookings assigned to provider."""
        query = (
            select(Booking)
            .where(Booking.provider_id == provider_id)
            .options(selectinload(Booking.job), selectinload(Booking.customer))
            .order_by(Booking.created_at.desc())
        )
        if status:
            query = query.where(Booking.status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())
