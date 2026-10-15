import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.repositories.notification import NotificationRepository
from app.services.base import BaseService


class NotificationService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.notif_repo = NotificationRepository(session)

    # ─────────────────────────────────────────────
    # Core creation
    # ─────────────────────────────────────────────

    async def create_notification(
        self,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create a notification for a user."""
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title.strip(),
            message=message.strip(),
            link_url=action_url,
            is_read=False,
            metadata_json=data or {},
        )
        self.session.add(notif)
        await self.session.flush()
        return notif

    # ─────────────────────────────────────────────
    # Typed event helpers
    # ─────────────────────────────────────────────

    async def notify_new_job(
        self,
        provider_user_id: uuid.UUID,
        job_title: str,
        job_id: uuid.UUID,
        city: str,
    ) -> None:
        """Notify a nearby provider that a new job is available."""
        await self.create_notification(
            user_id=provider_user_id,
            type=NotificationType.NEW_JOB,
            title="New Job Near You",
            message=f"A new job '{job_title}' is available in {city}. Be the first to quote!",
            action_url=f"/provider/jobs/{job_id}",
            data={"job_id": str(job_id)},
        )

    async def notify_bid_received(
        self,
        customer_user_id: uuid.UUID,
        provider_name: str,
        amount: float,
        job_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> None:
        """Notify customer that a provider submitted a bid on their job."""
        await self.create_notification(
            user_id=customer_user_id,
            type=NotificationType.BID_RECEIVED,
            title="New Quote Received",
            message=f"{provider_name} submitted a quote of ${amount:.2f} for your job.",
            action_url=f"/customer/jobs/{job_id}/quotes",
            data={"bid_id": str(bid_id), "job_id": str(job_id)},
        )

    async def notify_bid_accepted(
        self,
        provider_user_id: uuid.UUID,
        customer_name: str,
        amount: float,
        booking_id: uuid.UUID,
    ) -> None:
        """Notify provider that their bid was accepted and job is confirmed."""
        await self.create_notification(
            user_id=provider_user_id,
            type=NotificationType.BID_ACCEPTED,
            title="Quote Accepted — Job Confirmed!",
            message=f"{customer_name} accepted your quote of ${amount:.2f}. Escrow has been locked.",
            action_url=f"/provider/bookings/{booking_id}",
            data={"booking_id": str(booking_id)},
        )

    async def notify_job_cancelled(
        self,
        provider_user_id: uuid.UUID,
        job_title: str,
        job_id: uuid.UUID,
    ) -> None:
        """Notify provider that a job they bid on has been cancelled."""
        await self.create_notification(
            user_id=provider_user_id,
            type=NotificationType.JOB_CANCELLED,
            title="Job Cancelled",
            message=f"The job '{job_title}' has been cancelled by the customer.",
            action_url=f"/provider/jobs",
            data={"job_id": str(job_id)},
        )

    async def notify_job_completed(
        self,
        provider_user_id: uuid.UUID,
        amount: float,
        booking_id: uuid.UUID,
    ) -> None:
        """Notify provider that job is complete and payment has been released."""
        await self.create_notification(
            user_id=provider_user_id,
            type=NotificationType.JOB_COMPLETED,
            title="Payment Released",
            message=f"Job complete! ${amount:.2f} has been released from escrow to your account.",
            action_url=f"/provider/bookings/{booking_id}",
            data={"booking_id": str(booking_id)},
        )

    async def notify_review_received(
        self,
        provider_user_id: uuid.UUID,
        reviewer_name: str,
        rating: int,
        review_id: uuid.UUID,
    ) -> None:
        """Notify provider that a customer left them a review."""
        stars = "★" * rating + "☆" * (5 - rating)
        await self.create_notification(
            user_id=provider_user_id,
            type=NotificationType.REVIEW_RECEIVED,
            title="New Review Received",
            message=f"{reviewer_name} left you a {rating}-star review {stars}.",
            action_url=f"/provider/reviews",
            data={"review_id": str(review_id), "rating": rating},
        )

    # ─────────────────────────────────────────────
    # CRUD queries
    # ─────────────────────────────────────────────

    async def get_user_notifications(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[Notification]:
        """Fetch notifications for user."""
        return await self.notif_repo.get_user_notifications(user_id, skip=skip, limit=limit)

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Count unread notifications."""
        return await self.notif_repo.get_unread_count(user_id)

    async def mark_as_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        """Mark a single notification as read."""
        notif = await self.notif_repo.get_by_id(notification_id)
        if notif and notif.user_id == user_id:
            notif.is_read = True
            self.session.add(notif)
            await self.session.flush()
            return True
        return False

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for user."""
        return await self.notif_repo.mark_all_as_read(user_id)
