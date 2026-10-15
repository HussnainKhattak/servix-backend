import uuid
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ConflictException
from app.models.category import ServiceCategory
from app.models.provider_service import ProviderService
from app.models.provider import Provider
from app.repositories.category import CategoryRepository, ProviderServiceRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.base import BaseService


def slugify(text: str) -> str:
    """Generate a clean URL slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class CategoryService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.cat_repo = CategoryRepository(session)
        self.pro_service_repo = ProviderServiceRepository(session)

    async def list_active_categories(self) -> List[ServiceCategory]:
        """Fetch all public active service categories."""
        return await self.cat_repo.get_all_active()

    async def get_category_by_id(self, category_id: uuid.UUID) -> ServiceCategory:
        """Get single category details."""
        category = await self.cat_repo.get_by_id(category_id)
        if not category:
            raise EntityNotFoundException("ServiceCategory", category_id)
        return category

    async def create_category(self, data: CategoryCreate) -> ServiceCategory:
        """Admin creates a new service category."""
        slug = data.slug or slugify(data.name)
        existing = await self.cat_repo.get_by_slug(slug)
        if existing:
            raise ConflictException(f"A category with slug '{slug}' already exists.")

        category = ServiceCategory(
            name=data.name.strip(),
            slug=slug,
            icon=data.icon,
            description=data.description,
            avg_price_min=data.avg_price_min,
            avg_price_max=data.avg_price_max,
            is_active=data.is_active,
        )
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def update_category(self, category_id: uuid.UUID, data: CategoryUpdate) -> ServiceCategory:
        """Admin updates an existing service category."""
        category = await self.get_category_by_id(category_id)

        if data.name is not None:
            category.name = data.name.strip()
        if data.slug is not None:
            category.slug = data.slug.strip()
        if data.description is not None:
            category.description = data.description
        if data.icon is not None:
            category.icon = data.icon
        if data.avg_price_min is not None:
            category.avg_price_min = data.avg_price_min
        if data.avg_price_max is not None:
            category.avg_price_max = data.avg_price_max
        if data.is_active is not None:
            category.is_active = data.is_active

        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def add_provider_service(
        self, provider: Provider, category_id: uuid.UUID, custom_rate: Optional[float] = None
    ) -> ProviderService:
        """Provider attaches a service category to their profile."""
        category = await self.get_category_by_id(category_id)
        existing = await self.pro_service_repo.get_by_provider_and_category(provider.id, category.id)
        if existing:
            raise ConflictException("You have already added this service to your profile.")

        pro_service = ProviderService(
            provider_id=provider.id,
            category_id=category.id,
            custom_hourly_rate=custom_rate or provider.hourly_rate,
        )
        self.session.add(pro_service)
        await self.session.flush()
        await self.session.refresh(pro_service)
        return pro_service

    async def remove_provider_service(self, provider: Provider, category_id: uuid.UUID) -> bool:
        """Provider removes a service category from their profile."""
        existing = await self.pro_service_repo.get_by_provider_and_category(provider.id, category_id)
        if not existing:
            raise EntityNotFoundException("ProviderService", category_id)

        await self.session.delete(existing)
        await self.session.flush()
        return True
