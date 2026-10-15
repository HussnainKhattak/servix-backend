import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.category import ServiceCategory
from app.models.provider_service import ProviderService
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[ServiceCategory, CategoryCreate, CategoryUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(ServiceCategory, session)

    async def get_by_slug(self, slug: str) -> Optional[ServiceCategory]:
        """Find category by unique URL slug."""
        result = await self.session.execute(
            select(ServiceCategory).where(ServiceCategory.slug == slug.lower().strip())
        )
        return result.scalars().first()

    async def get_all_active(self) -> List[ServiceCategory]:
        """Fetch all active categories ordered by sort_order."""
        result = await self.session.execute(
            select(ServiceCategory)
            .where(ServiceCategory.is_active.is_(True))
            .order_by(ServiceCategory.name.asc())
        )
        return list(result.scalars().all())


class ProviderServiceRepository(BaseRepository[ProviderService, ProviderService, ProviderService]):
    def __init__(self, session: AsyncSession):
        super().__init__(ProviderService, session)

    async def get_by_provider_and_category(
        self, provider_id: uuid.UUID, category_id: uuid.UUID
    ) -> Optional[ProviderService]:
        """Check if provider already has this service assigned."""
        result = await self.session.execute(
            select(ProviderService).where(
                ProviderService.provider_id == provider_id,
                ProviderService.category_id == category_id,
            )
        )
        return result.scalars().first()

    async def get_provider_services(self, provider_id: uuid.UUID) -> List[ProviderService]:
        """Fetch all services attached to a provider profile."""
        result = await self.session.execute(
            select(ProviderService)
            .where(ProviderService.provider_id == provider_id)
            .options(selectinload(ProviderService.category))
        )
        return list(result.scalars().all())
