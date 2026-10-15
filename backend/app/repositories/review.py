import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.review import Review
from app.schemas.review import ReviewCreate
from app.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review, ReviewCreate, ReviewCreate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Review, session)

    async def get_by_id_with_relations(self, review_id: uuid.UUID) -> Optional[Review]:
        """Fetch review with customer eagerly loaded."""
        result = await self.session.execute(
            select(Review)
            .where(Review.id == review_id)
            .options(selectinload(Review.customer))
        )
        return result.scalars().first()

    async def get_by_booking_id(self, booking_id: uuid.UUID) -> Optional[Review]:
        """Fetch review attached to a booking."""
        result = await self.session.execute(
            select(Review).where(Review.booking_id == booking_id)
        )
        return result.scalars().first()

    async def get_provider_reviews(
        self,
        provider_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Review]:
        """Fetch published reviews for a provider."""
        result = await self.session.execute(
            select(Review)
            .where(
                Review.provider_id == provider_id,
                Review.is_published.is_(True),
            )
            .options(selectinload(Review.customer))
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_reviews(
        self,
        is_flagged: Optional[bool] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Review]:
        """Admin: fetch all reviews with optional filters."""
        query = select(Review).options(selectinload(Review.customer))
        if is_flagged is not None:
            query = query.where(Review.is_flagged == is_flagged)
        if is_published is not None:
            query = query.where(Review.is_published == is_published)
        query = query.order_by(Review.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def calculate_provider_aggregate_rating(
        self, provider_id: uuid.UUID
    ) -> Tuple[float, int]:
        """Calculate average rating and count of published reviews for a provider."""
        result = await self.session.execute(
            select(
                func.coalesce(func.avg(Review.rating), 0.0),
                func.count(Review.id),
            ).where(
                Review.provider_id == provider_id,
                Review.is_published.is_(True),
            )
        )
        avg_rating, count = result.first() or (0.0, 0)
        return round(float(avg_rating), 2), int(count)
