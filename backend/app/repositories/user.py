import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email address."""
        result = await self.session.execute(
            select(User)
            .where(User.email == email.lower().strip())
            .options(selectinload(User.provider_profile))
        )
        return result.scalars().first()

    async def get_by_id_with_profile(self, user_id: uuid.UUID) -> Optional[User]:
        """Find user by id with provider profile eagerly loaded."""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.provider_profile))
        )
        return result.scalars().first()
