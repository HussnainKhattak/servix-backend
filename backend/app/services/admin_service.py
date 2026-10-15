import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, BadRequestException, ConflictException
from app.models.enums import JobStatus, BookingStatus, EscrowStatus, UserRole
from app.models.user import User
from app.models.provider import Provider
from app.models.job import Job
from app.models.booking import Booking
from app.models.review import Review
from app.models.category import ServiceCategory
from app.schemas.admin import AdminCategoryCreate, AdminCategoryUpdate
from app.services.base import BaseService


class AdminService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    # ─────────────────────────────────────────────────────────
    # DASHBOARD & REPORTS
    # ─────────────────────────────────────────────────────────

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Aggregate high-level platform statistics for the Admin panel."""
        user_count = await self.session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.CUSTOMER)
        ) or 0

        provider_count = await self.session.scalar(
            select(func.count(Provider.id))
        ) or 0

        total_jobs = await self.session.scalar(
            select(func.count(Job.id))
        ) or 0

        completed_jobs = await self.session.scalar(
            select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED)
        ) or 0

        active_jobs = await self.session.scalar(
            select(func.count(Job.id)).where(
                Job.status.in_([JobStatus.OPEN, JobStatus.BIDDING, JobStatus.ASSIGNED, JobStatus.IN_PROGRESS])
            )
        ) or 0

        finance_result = await self.session.execute(
            select(
                func.coalesce(func.sum(Booking.agreed_price), 0.0),
                func.coalesce(func.sum(Booking.platform_fee), 0.0),
            ).where(Booking.escrow_status == EscrowStatus.RELEASED)
        )
        total_volume, total_platform_revenue = finance_result.first() or (0.0, 0.0)

        return {
            "total_users": user_count,
            "total_providers": provider_count,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "active_jobs": active_jobs,
            "total_volume": round(float(total_volume), 2),
            "total_platform_revenue": round(float(total_platform_revenue), 2),
        }

    async def get_reports(self) -> Dict[str, Any]:
        """Detailed statistical reports across users, providers, jobs, escrow, and quality."""
        total_users = await self.session.scalar(select(func.count(User.id))) or 0
        suspended_users = await self.session.scalar(select(func.count(User.id)).where(User.is_active == False)) or 0
        total_providers = await self.session.scalar(select(func.count(Provider.id))) or 0
        verified_providers = await self.session.scalar(select(func.count(Provider.id)).where(Provider.is_license_verified == True)) or 0

        total_jobs = await self.session.scalar(select(func.count(Job.id))) or 0
        open_jobs = await self.session.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.OPEN)) or 0
        active_jobs = await self.session.scalar(select(func.count(Job.id)).where(Job.status.in_([JobStatus.BIDDING, JobStatus.ASSIGNED, JobStatus.IN_PROGRESS]))) or 0
        completed_jobs = await self.session.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED)) or 0
        cancelled_jobs = await self.session.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.CANCELLED)) or 0
        disputed_jobs = await self.session.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.DISPUTE)) or 0

        total_bookings = await self.session.scalar(select(func.count(Booking.id))) or 0
        finance_result = await self.session.execute(
            select(
                func.coalesce(func.sum(Booking.agreed_price), 0.0),
                func.coalesce(func.sum(Booking.platform_fee), 0.0),
            ).where(Booking.escrow_status == EscrowStatus.RELEASED)
        )
        total_volume, total_revenue = finance_result.first() or (0.0, 0.0)

        review_stats = await self.session.execute(
            select(
                func.count(Review.id),
                func.coalesce(func.avg(Review.rating), 0.0),
            ).where(Review.is_published == True)
        )
        total_reviews, avg_rating = review_stats.first() or (0, 0.0)

        return {
            "total_users": total_users,
            "total_providers": total_providers,
            "total_jobs": total_jobs,
            "open_jobs": open_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "cancelled_jobs": cancelled_jobs,
            "disputed_jobs": disputed_jobs,
            "total_bookings": total_bookings,
            "total_escrow_volume": round(float(total_volume), 2),
            "total_platform_revenue": round(float(total_revenue), 2),
            "total_reviews": int(total_reviews),
            "avg_platform_rating": round(float(avg_rating), 2),
            "verified_providers": verified_providers,
            "suspended_users": suspended_users,
        }

    # ─────────────────────────────────────────────────────────
    # USER MANAGEMENT
    # ─────────────────────────────────────────────────────────

    async def list_users(
        self,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[User]:
        """Admin: list registered platform users."""
        query = select(User)
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if search:
            search_pattern = f"%{search.strip().lower()}%"
            query = query.where(
                (func.lower(User.full_name).ilike(search_pattern)) |
                (func.lower(User.email).ilike(search_pattern))
            )
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_details(self, user_id: uuid.UUID) -> User:
        """Admin: get full user profile details."""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.provider_profile))
        )
        user = result.scalars().first()
        if not user:
            raise EntityNotFoundException("User", user_id)
        return user

    async def set_user_active_status(
        self, user_id: uuid.UUID, is_active: bool
    ) -> User:
        """Admin suspends or restores a user account."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()
        if not user:
            raise EntityNotFoundException("User", user_id)

        user.is_active = is_active
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    # ─────────────────────────────────────────────────────────
    # PROVIDER MANAGEMENT
    # ─────────────────────────────────────────────────────────

    async def list_providers(
        self,
        is_verified: Optional[bool] = None,
        is_available: Optional[bool] = None,
        trade: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Provider]:
        """Admin: list service providers."""
        query = select(Provider).options(selectinload(Provider.user))
        if is_verified is not None:
            query = query.where(Provider.is_license_verified == is_verified)
        if is_available is not None:
            query = query.where(Provider.is_available == is_available)
        if trade:
            query = query.where(Provider.trade.ilike(f"%{trade.strip()}%"))

        query = query.order_by(Provider.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_provider_details(self, provider_id: uuid.UUID) -> Provider:
        """Admin: get detailed provider record with user relation."""
        result = await self.session.execute(
            select(Provider)
            .where(Provider.id == provider_id)
            .options(
                selectinload(Provider.user),
                selectinload(Provider.services),
            )
        )
        provider = result.scalars().first()
        if not provider:
            raise EntityNotFoundException("Provider", provider_id)
        return provider

    async def set_provider_verification(
        self, provider_id: uuid.UUID, is_verified: bool
    ) -> Provider:
        """Admin verifies or un-verifies a provider's trade license."""
        result = await self.session.execute(
            select(Provider).where(Provider.id == provider_id).options(selectinload(Provider.user))
        )
        provider = result.scalars().first()
        if not provider:
            raise EntityNotFoundException("Provider", provider_id)

        provider.is_license_verified = is_verified
        self.session.add(provider)
        await self.session.flush()
        await self.session.refresh(provider)
        return provider

    # ─────────────────────────────────────────────────────────
    # CATEGORY MANAGEMENT
    # ─────────────────────────────────────────────────────────

    async def list_categories(self) -> List[ServiceCategory]:
        """Admin: list all categories (including inactive)."""
        result = await self.session.execute(
            select(ServiceCategory).order_by(ServiceCategory.name.asc())
        )
        return list(result.scalars().all())

    async def create_category(self, data: AdminCategoryCreate) -> ServiceCategory:
        """Admin: create a new service category."""
        existing = await self.session.scalar(
            select(ServiceCategory).where(ServiceCategory.slug == data.slug.strip().lower())
        )
        if existing:
            raise ConflictException(f"Category slug '{data.slug}' is already in use.")

        category = ServiceCategory(
            name=data.name.strip(),
            slug=data.slug.strip().lower(),
            description=data.description.strip() if data.description else None,
            icon=data.icon or "🔧",
            avg_price_min=data.avg_price_min,
            avg_price_max=data.avg_price_max,
            is_active=data.is_active,
        )
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def update_category(self, category_id: uuid.UUID, data: AdminCategoryUpdate) -> ServiceCategory:
        """Admin: update service category details."""
        result = await self.session.execute(
            select(ServiceCategory).where(ServiceCategory.id == category_id)
        )
        category = result.scalars().first()
        if not category:
            raise EntityNotFoundException("Category", category_id)

        if data.name is not None:
            category.name = data.name.strip()
        if data.slug is not None:
            category.slug = data.slug.strip().lower()
        if data.description is not None:
            category.description = data.description.strip()
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

    async def delete_category(self, category_id: uuid.UUID) -> bool:
        """Admin: soft-delete or remove service category."""
        result = await self.session.execute(
            select(ServiceCategory).where(ServiceCategory.id == category_id)
        )
        category = result.scalars().first()
        if not category:
            raise EntityNotFoundException("Category", category_id)

        category.is_active = False
        self.session.add(category)
        await self.session.flush()
        return True

    # ─────────────────────────────────────────────────────────
    # JOB MODERATION
    # ─────────────────────────────────────────────────────────

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        category_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Job]:
        """Admin: list jobs across the platform with customer relation loaded."""
        query = select(Job).options(selectinload(Job.customer), selectinload(Job.category))
        if status:
            query = query.where(Job.status == status)
        if category_id:
            query = query.where(Job.category_id == category_id)

        query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cancel_job_admin(self, job_id: uuid.UUID, reason: Optional[str] = None) -> Job:
        """Admin force-cancels a job in any active state."""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id).options(selectinload(Job.customer))
        )
        job = result.scalars().first()
        if not job:
            raise EntityNotFoundException("Job", job_id)

        job.status = JobStatus.CANCELLED
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    # ─────────────────────────────────────────────────────────
    # REVIEW MODERATION
    # ─────────────────────────────────────────────────────────

    async def list_reviews(
        self,
        is_flagged: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Review]:
        """Admin: list reviews with moderation flags."""
        query = select(Review).options(selectinload(Review.customer), selectinload(Review.provider))
        if is_flagged is not None:
            query = query.where(Review.is_flagged == is_flagged)

        query = query.order_by(Review.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def flag_review(self, review_id: uuid.UUID, reason: str) -> Review:
        """Admin flags a review."""
        result = await self.session.execute(select(Review).where(Review.id == review_id))
        review = result.scalars().first()
        if not review:
            raise EntityNotFoundException("Review", review_id)

        review.is_flagged = True
        review.flag_reason = reason.strip()
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def delete_review(self, review_id: uuid.UUID) -> bool:
        """Admin unpublishes / removes an abusive review."""
        result = await self.session.execute(select(Review).where(Review.id == review_id))
        review = result.scalars().first()
        if not review:
            raise EntityNotFoundException("Review", review_id)

        review.is_published = False
        self.session.add(review)
        await self.session.flush()
        return True
