import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ConflictException
from app.models.favorite import Favorite
from app.models.user import User
from app.repositories.favorite import FavoriteRepository
from app.repositories.provider import ProviderRepository
from app.services.base import BaseService


class FavoriteService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.fav_repo = FavoriteRepository(session)
        self.pro_repo = ProviderRepository(session)

    async def add_favorite(self, customer: User, provider_id: uuid.UUID) -> Favorite:
        """Customer favorites a service provider."""
        provider = await self.pro_repo.get_by_id(provider_id)
        if not provider:
            raise EntityNotFoundException("Provider", provider_id)

        existing = await self.fav_repo.get_by_customer_and_provider(customer.id, provider.id)
        if existing:
            raise ConflictException("Provider is already in your favorites.")

        fav = Favorite(customer_id=customer.id, provider_id=provider.id)
        self.session.add(fav)
        await self.session.flush()

        # Load relationships for serialization
        from app.models.provider import Provider
        result = await self.session.execute(
            select(Favorite)
            .where(Favorite.id == fav.id)
            .options(selectinload(Favorite.provider).selectinload(Provider.user))
        )
        return result.scalars().first()

    async def remove_favorite(self, customer: User, provider_id: uuid.UUID) -> bool:
        """Customer unfavorites a service provider."""
        return await self.fav_repo.remove_favorite(customer.id, provider_id)

    async def list_favorites(self, customer: User, skip: int = 0, limit: int = 50) -> List[Favorite]:
        """Fetch customer's favorite providers."""
        return await self.fav_repo.get_customer_favorites(customer.id, skip=skip, limit=limit)
