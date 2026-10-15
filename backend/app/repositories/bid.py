import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bid import Bid
from app.models.provider import Provider
from app.models.enums import BidStatus
from app.schemas.bid import BidCreate, BidUpdate
from app.repositories.base import BaseRepository


class BidRepository(BaseRepository[Bid, BidCreate, BidUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Bid, session)

    async def get_by_job_and_provider(
        self, job_id: uuid.UUID, provider_id: uuid.UUID
    ) -> Optional[Bid]:
        """Check if a provider already placed a bid on a job."""
        result = await self.session.execute(
            select(Bid).where(
                Bid.job_id == job_id,
                Bid.provider_id == provider_id,
            )
        )
        return result.scalars().first()

    async def get_bids_for_job(self, job_id: uuid.UUID) -> List[Bid]:
        """Fetch all submitted bids for a job, ordered by price."""
        result = await self.session.execute(
            select(Bid)
            .where(Bid.job_id == job_id)
            .options(
                selectinload(Bid.provider).selectinload(Provider.user)
            )
            .order_by(Bid.amount.asc())
        )
        return list(result.scalars().all())

    async def get_provider_bids(
        self, provider_id: uuid.UUID, status: Optional[BidStatus] = None
    ) -> List[Bid]:
        """Fetch all bids submitted by a specific provider."""
        query = (
            select(Bid)
            .where(Bid.provider_id == provider_id)
            .options(
                selectinload(Bid.job),
                selectinload(Bid.provider).selectinload(Provider.user),
            )
            .order_by(Bid.created_at.desc())
        )
        if status:
            query = query.where(Bid.status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())
