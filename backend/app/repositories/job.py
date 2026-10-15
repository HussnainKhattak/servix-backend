import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job
from app.models.enums import JobStatus
from app.schemas.job import JobCreate, JobUpdate
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job, JobCreate, JobUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_by_id_with_relations(self, id: uuid.UUID) -> Optional[Job]:
        """Fetch job with category, customer, images, and bids eagerly loaded."""
        result = await self.session.execute(
            select(Job)
            .where(Job.id == id)
            .options(
                selectinload(Job.category),
                selectinload(Job.customer),
                selectinload(Job.images),
                selectinload(Job.bids),
            )
        )
        return result.scalars().first()

    async def get_customer_jobs(
        self,
        customer_id: uuid.UUID,
        status: Optional[JobStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Job]:
        """Fetch all jobs posted by a specific customer."""
        query = (
            select(Job)
            .where(Job.customer_id == customer_id)
            .options(selectinload(Job.category), selectinload(Job.images), selectinload(Job.bids))
            .order_by(Job.created_at.desc())
        )
        if status:
            query = query.where(Job.status == status)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_open_jobs_feed(
        self,
        category_id: Optional[uuid.UUID] = None,
        city: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Job]:
        """Fetch active open jobs for providers to quote on."""
        query = (
            select(Job)
            .where(Job.status.in_([JobStatus.OPEN, JobStatus.BIDDING]))
            .options(selectinload(Job.category), selectinload(Job.images), selectinload(Job.bids))
            .order_by(Job.created_at.desc())
        )
        if category_id:
            query = query.where(Job.category_id == category_id)
        if city:
            query = query.where(Job.city.ilike(f"%{city}%"))

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
