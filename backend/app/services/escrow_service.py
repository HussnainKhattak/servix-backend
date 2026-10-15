import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import EntityNotFoundException, BadRequestException, ForbiddenException
from app.models.enums import JobStatus, BidStatus, BookingStatus, EscrowStatus, UserRole
from app.models.booking import Booking
from app.models.user import User
from app.models.provider import Provider
from app.repositories.bid import BidRepository
from app.repositories.job import JobRepository
from app.repositories.booking import BookingRepository
from app.repositories.provider import ProviderRepository
from app.schemas.booking import BookingCreate
from app.services.base import BaseService


class EscrowBookingService(BaseService):
    """
    Handles the complete marketplace workflow:
    Accepting bids -> Locking escrow funds -> Starting work -> Completing jobs -> Releasing payouts.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.job_repo = JobRepository(session)
        self.bid_repo = BidRepository(session)
        self.booking_repo = BookingRepository(session)
        self.provider_repo = ProviderRepository(session)

    async def accept_bid_and_book(
        self, customer: User, data: BookingCreate
    ) -> Booking:
        """Customer accepts a bid, locks escrow, and assigns the job."""
        job = await self.job_repo.get_by_id(data.job_id)
        if not job:
            raise EntityNotFoundException("Job", data.job_id)

        if job.customer_id != customer.id and customer.role != UserRole.ADMIN:
            raise ForbiddenException("You can only accept bids on your own jobs.")

        bid = await self.bid_repo.get_by_id(data.bid_id)
        if not bid or bid.job_id != job.id:
            raise EntityNotFoundException("Bid", data.bid_id)

        if bid.status != BidStatus.PENDING:
            raise BadRequestException("This bid is no longer pending.")

        # Calculate platform fee and provider payout
        fee_rate = settings.PLATFORM_FEE_PERCENTAGE / 100.0
        platform_fee = round(bid.amount * fee_rate, 2)
        provider_payout = round(bid.amount - platform_fee, 2)

        # Mark chosen bid as accepted
        bid.status = BidStatus.ACCEPTED

        # Mark all other competing bids on this job as rejected
        other_bids = await self.bid_repo.get_bids_for_job(job.id)
        for b in other_bids:
            if b.id != bid.id and b.status == BidStatus.PENDING:
                b.status = BidStatus.REJECTED

        # Update job status
        job.status = JobStatus.ASSIGNED

        # Create confirmed booking with funds in escrow HOLDING
        booking = Booking(
            job_id=job.id,
            bid_id=bid.id,
            customer_id=customer.id,
            provider_id=bid.provider_id,
            agreed_price=bid.amount,
            platform_fee=platform_fee,
            provider_payout=provider_payout,
            status=BookingStatus.CONFIRMED,
            escrow_status=EscrowStatus.HOLDING,
            scheduled_date=data.scheduled_date,
            scheduled_time=data.scheduled_time,
        )
        self.session.add(booking)
        await self.session.flush()
        await self.session.refresh(booking)
        booking_details = await self.get_booking_details(booking.id)

        # Notify provider about bid acceptance & job assignment
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.session)
            provider_user_id = booking_details.provider.user_id if booking_details.provider else None
            if provider_user_id:
                await notif_service.notify_bid_accepted(
                    provider_user_id=provider_user_id,
                    customer_name=customer.full_name,
                    amount=booking.agreed_price,
                    booking_id=booking.id,
                )
        except Exception:
            pass

        return booking_details

    async def get_booking_details(self, booking_id: uuid.UUID) -> Booking:
        """Retrieve booking with all relationships loaded."""
        booking = await self.booking_repo.get_by_id_with_relations(booking_id)
        if not booking:
            raise EntityNotFoundException("Booking", booking_id)
        return booking

    async def get_customer_bookings(
        self, customer: User, status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """Fetch bookings for customer."""
        return await self.booking_repo.get_by_customer(customer.id, status=status)

    async def get_provider_bookings(
        self, provider: Provider, status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """Fetch bookings assigned to provider."""
        return await self.booking_repo.get_by_provider(provider.id, status=status)

    async def start_job(self, provider: Provider, booking_id: uuid.UUID) -> Booking:
        """Provider starts job on site."""
        booking = await self.get_booking_details(booking_id)
        if booking.provider_id != provider.id:
            raise ForbiddenException("You are not assigned to this booking.")

        if booking.status != BookingStatus.CONFIRMED:
            raise BadRequestException(f"Cannot start booking in '{booking.status.value}' state.")

        booking.status = BookingStatus.IN_PROGRESS
        job = await self.job_repo.get_by_id(booking.job_id)
        if job:
            job.status = JobStatus.IN_PROGRESS

        self.session.add(booking)
        await self.session.flush()
        return await self.get_booking_details(booking_id)

    async def confirm_completion_and_release_escrow(
        self, customer: User, booking_id: uuid.UUID
    ) -> Booking:
        """Customer confirms work is complete; releases escrow payment to provider."""
        booking = await self.get_booking_details(booking_id)
        if booking.customer_id != customer.id and customer.role != UserRole.ADMIN:
            raise ForbiddenException("Only the customer who hired the pro can confirm completion.")

        if booking.escrow_status != EscrowStatus.HOLDING:
            raise BadRequestException("Escrow funds have already been processed.")

        booking.status = BookingStatus.COMPLETED
        booking.escrow_status = EscrowStatus.RELEASED
        booking.completed_at = datetime.now(timezone.utc)

        # Update job status to COMPLETED
        job = await self.job_repo.get_by_id(booking.job_id)
        if job:
            job.status = JobStatus.COMPLETED

        # Increment provider completed jobs counter
        provider = await self.provider_repo.get_by_id(booking.provider_id)
        if provider:
            provider.jobs_completed += 1
            self.session.add(provider)

        self.session.add(booking)
        await self.session.flush()
        updated_booking = await self.get_booking_details(booking_id)

        # Notify provider about payout release
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.session)
            provider_user_id = updated_booking.provider.user_id if updated_booking.provider else None
            if provider_user_id:
                await notif_service.notify_job_completed(
                    provider_user_id=provider_user_id,
                    amount=booking.provider_payout,
                    booking_id=booking.id,
                )
        except Exception:
            pass

        return updated_booking

    async def raise_dispute(
        self, user: User, booking_id: uuid.UUID, reason: str
    ) -> Booking:
        """Customer or Provider reports a dispute on the booking."""
        booking = await self.get_booking_details(booking_id)
        is_party = (booking.customer_id == user.id) or (booking.provider and booking.provider.user_id == user.id)
        if not is_party and user.role != UserRole.ADMIN:
            raise ForbiddenException("You are not a participant in this booking.")

        booking.status = BookingStatus.DISPUTED
        booking.escrow_status = EscrowStatus.DISPUTED
        booking.cancellation_reason = reason

        self.session.add(booking)
        await self.session.flush()
        return await self.get_booking_details(booking_id)
