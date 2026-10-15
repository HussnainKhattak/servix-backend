import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate
from app.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[Provider, ProviderCreate, ProviderUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Provider, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Provider]:
        """Find provider profile by user id with relationships loaded."""
        result = await self.session.execute(
            select(Provider)
            .where(Provider.user_id == user_id)
            .options(selectinload(Provider.user), selectinload(Provider.services))
        )
        return result.scalars().first()

    async def get_available_by_trade(
        self,
        trade: Optional[str] = None,
        city: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Provider]:
        """Find available verified providers filtered by trade and location."""
        query = (
            select(Provider)
            .where(Provider.is_available.is_(True))
            .options(selectinload(Provider.user))
            .order_by(Provider.avg_rating.desc(), Provider.jobs_completed.desc())
        )
        if trade:
            query = query.where(Provider.trade.ilike(f"%{trade}%"))
        if city:
            query = query.where(Provider.city.ilike(f"%{city}%"))

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
