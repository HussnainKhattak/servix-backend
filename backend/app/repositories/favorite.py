import uuid
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.favorite import Favorite
from app.models.provider import Provider
from app.repositories.base import BaseRepository


class FavoriteRepository(BaseRepository[Favorite, Favorite, Favorite]):
    def __init__(self, session: AsyncSession):
        super().__init__(Favorite, session)

    async def get_by_customer_and_provider(
        self, customer_id: uuid.UUID, provider_id: uuid.UUID
    ) -> Optional[Favorite]:
        """Check if customer favorited provider."""
        result = await self.session.execute(
            select(Favorite).where(
                Favorite.customer_id == customer_id,
                Favorite.provider_id == provider_id,
            )
        )
        return result.scalars().first()

    async def get_customer_favorites(
        self, customer_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[Favorite]:
        """Fetch all favorited providers for a customer."""
        result = await self.session.execute(
            select(Favorite)
            .where(Favorite.customer_id == customer_id)
            .options(
                selectinload(Favorite.provider).selectinload(Provider.user),
            )
            .order_by(Favorite.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def remove_favorite(self, customer_id: uuid.UUID, provider_id: uuid.UUID) -> bool:
        """Remove a favorite entry."""
        result = await self.session.execute(
            delete(Favorite).where(
                Favorite.customer_id == customer_id,
                Favorite.provider_id == provider_id,
            )
        )
        await self.session.flush()
        return result.rowcount > 0
