import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    EntityNotFoundException, ConflictException, BadRequestException,
    ForbiddenException,
)
from app.models.enums import BookingStatus, NotificationType, UserRole
from app.models.review import Review
from app.models.user import User
from app.models.provider import Provider
from app.repositories.review import ReviewRepository
from app.repositories.booking import BookingRepository
from app.repositories.provider import ProviderRepository
from app.schemas.review import ReviewCreate
from app.services.base import BaseService


class ReviewService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.review_repo = ReviewRepository(session)
        self.booking_repo = BookingRepository(session)
        self.provider_repo = ProviderRepository(session)

    async def submit_review(self, customer: User, data: ReviewCreate) -> Review:
        """Customer leaves a review and rating for a completed booking."""
        booking = await self.booking_repo.get_by_id(data.booking_id)
        if not booking:
            raise EntityNotFoundException("Booking", data.booking_id)

        if booking.customer_id != customer.id:
            raise ForbiddenException("You can only review jobs you booked.")

        if booking.status != BookingStatus.COMPLETED:
            raise BadRequestException("Reviews can only be submitted after the job is completed.")

        existing = await self.review_repo.get_by_booking_id(booking.id)
        if existing:
            raise ConflictException("A review has already been submitted for this booking.")

        review = Review(
            booking_id=booking.id,
            customer_id=customer.id,
            provider_id=booking.provider_id,
            rating=data.rating,
            comment=data.comment,
            is_published=True,
        )
        self.session.add(review)
        await self.session.flush()

        # Recalculate and update provider's average rating and review count
        avg_rating, count = await self.review_repo.calculate_provider_aggregate_rating(booking.provider_id)
        provider = await self.provider_repo.get_by_id(booking.provider_id)
        if provider:
            provider.avg_rating = avg_rating
            provider.reviews_count = count
            self.session.add(provider)

        await self.session.flush()

        # Fire notification to provider
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.session)
            await notif_service.notify_review_received(
                provider_user_id=provider.user_id if provider else booking.provider_id,
                reviewer_name=customer.full_name,
                rating=data.rating,
                review_id=review.id,
            )
        except Exception:
            pass  # Notifications are non-critical

        return await self.review_repo.get_by_id_with_relations(review.id)

    async def provider_reply_to_review(
        self, provider: Provider, review_id: uuid.UUID, reply_text: str
    ) -> Review:
        """Provider posts a public reply to a customer review."""
        review = await self.review_repo.get_by_id_with_relations(review_id)
        if not review:
            raise EntityNotFoundException("Review", review_id)

        if review.provider_id != provider.id:
            raise ForbiddenException("You can only reply to reviews about your own services.")

        if review.provider_reply:
            raise ConflictException("You have already replied to this review.")

        review.provider_reply = reply_text.strip()
        review.replied_at = datetime.now(timezone.utc)
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def flag_review(
        self, review_id: uuid.UUID, reason: str
    ) -> Review:
        """Admin flags a review for moderation."""
        review = await self.review_repo.get_by_id_with_relations(review_id)
        if not review:
            raise EntityNotFoundException("Review", review_id)
        review.is_flagged = True
        review.flag_reason = reason
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def delete_review(self, review_id: uuid.UUID) -> bool:
        """Admin removes a review (unpublishes it)."""
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            raise EntityNotFoundException("Review", review_id)
        review.is_published = False
        self.session.add(review)
        await self.session.flush()
        return True

    async def get_provider_reviews(
        self, provider_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[Review]:
        """Fetch all public published reviews for a service provider."""
        return await self.review_repo.get_provider_reviews(provider_id, skip=skip, limit=limit)

    async def get_all_reviews(
        self,
        is_flagged: Optional[bool] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Review]:
        """Admin: list all reviews with optional filters."""
        return await self.review_repo.get_all_reviews(
            is_flagged=is_flagged, is_published=is_published, skip=skip, limit=limit
        )
