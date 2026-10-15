import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ForbiddenException, BadRequestException
from app.models.enums import JobStatus, UserRole
from app.models.job import Job, JobImage
from app.models.user import User
from app.models.provider import Provider
from app.repositories.job import JobRepository
from app.repositories.bid import BidRepository
from app.schemas.job import JobCreate, JobUpdate
from app.services.base import BaseService
from app.utils.geo import calculate_haversine_distance, is_within_radius


class JobService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.job_repo = JobRepository(session)
        self.bid_repo = BidRepository(session)

    async def create_job(self, customer: User, data: JobCreate) -> Job:
        """Create a new service job broadcast by a customer."""
        category_id = data.category_id
        if not category_id:
            from app.models.category import ServiceCategory
            from sqlalchemy import select
            if getattr(data, "category_name", None):
                cat_match = await self.session.execute(
                    select(ServiceCategory.id).where(
                        ServiceCategory.name.ilike(f"%{data.category_name}%")
                        | ServiceCategory.slug.ilike(f"%{data.category_name}%")
                    )
                )
                category_id = cat_match.scalar_one_or_none()
            if not category_id:
                fallback_cat = await self.session.execute(select(ServiceCategory.id).limit(1))
                category_id = fallback_cat.scalar_one_or_none()

        job = Job(
            customer_id=customer.id,
            category_id=category_id,
            title=data.title.strip(),
            description=data.description.strip(),
            urgency=data.urgency,
            status=JobStatus.OPEN,
            target_budget=data.target_budget,
            address=data.address.strip(),
            city=data.city.strip(),
            state=data.state.strip(),
            zip_code=data.zip_code.strip(),
            latitude=data.latitude,
            longitude=data.longitude,
        )
        self.session.add(job)
        await self.session.flush()

        if data.image_urls:
            for idx, url in enumerate(data.image_urls):
                img = JobImage(job_id=job.id, image_url=url, is_cover=(idx == 0))
                self.session.add(img)

        await self.session.flush()
        await self.session.refresh(job)
        return await self.get_job_details(job.id)

    async def get_job_details(self, job_id: uuid.UUID) -> Job:
        """Retrieve full details of a job with relationships loaded."""
        job = await self.job_repo.get_by_id_with_relations(job_id)
        if not job:
            raise EntityNotFoundException("Job", job_id)
        return job

    async def get_customer_jobs(
        self, customer: User, status: Optional[JobStatus] = None, skip: int = 0, limit: int = 50
    ) -> List[Job]:
        """Fetch all jobs posted by the customer."""
        return await self.job_repo.get_customer_jobs(customer.id, status=status, skip=skip, limit=limit)

    async def get_nearby_jobs_for_provider(
        self,
        provider: Provider,
        category_id: Optional[uuid.UUID] = None,
        max_distance_miles: Optional[float] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Tuple[Job, Optional[float]]]:
        """
        Fetch available open jobs near the provider's location.
        Returns a list of tuples: (Job, distance_in_miles).
        """
        open_jobs = await self.job_repo.get_open_jobs_feed(category_id=category_id, city=provider.city, skip=0, limit=200)

        effective_radius = max_distance_miles or provider.service_radius_miles or 25.0
        results: List[Tuple[Job, Optional[float]]] = []

        for job in open_jobs:
            distance: Optional[float] = None
            if job.latitude and job.longitude and provider.latitude and provider.longitude:
                distance = calculate_haversine_distance(
                    job.latitude, job.longitude, provider.latitude, provider.longitude
                )
                if distance <= effective_radius:
                    results.append((job, distance))
            else:
                # If coords not available, match by city or zip code
                if not job.city or not provider.city or job.city.lower() == provider.city.lower():
                    results.append((job, None))

        # Sort by distance (if available) then newest
        results.sort(key=lambda item: (item[1] if item[1] is not None else 999.0))
        return results[skip : skip + limit]

    async def cancel_job(self, customer: User, job_id: uuid.UUID) -> Job:
        """Customer cancels an open or bidding job."""
        job = await self.get_job_details(job_id)
        if job.customer_id != customer.id and customer.role != UserRole.ADMIN:
            raise ForbiddenException("You can only cancel your own jobs.")

        if job.status not in [JobStatus.OPEN, JobStatus.BIDDING]:
            raise BadRequestException(f"Jobs with status '{job.status.value}' cannot be cancelled.")

        job.status = JobStatus.CANCELLED
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)

        # Notify any providers who submitted bids on this job
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.session)
            bids = await self.bid_repo.get_bids_for_job(job.id)
            for b in bids:
                if b.provider and b.provider.user_id:
                    await notif_service.notify_job_cancelled(
                        provider_user_id=b.provider.user_id,
                        job_title=job.title,
                        job_id=job.id,
                    )
        except Exception:
            pass

        return job

    async def add_job_images(self, job_id: uuid.UUID, image_urls: List[str]) -> List[JobImage]:
        """Add additional photo attachments to a job."""
        job = await self.get_job_details(job_id)
        images = []
        for url in image_urls:
            img = JobImage(job_id=job.id, image_url=url, is_cover=False)
            self.session.add(img)
            images.append(img)
        await self.session.flush()
        return images
