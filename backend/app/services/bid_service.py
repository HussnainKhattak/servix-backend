import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ConflictException, BadRequestException, ForbiddenException
from app.models.enums import JobStatus, BidStatus
from app.models.bid import Bid
from app.models.provider import Provider
from app.models.user import User
from app.repositories.bid import BidRepository
from app.repositories.job import JobRepository
from app.schemas.bid import BidCreate, BidUpdate
from app.services.base import BaseService


def parse_optional_datetime(val: Optional[str]) -> Optional[datetime]:
    """Safely parse an ISO date string or return None if human text."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


class BidService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.bid_repo = BidRepository(session)
        self.job_repo = JobRepository(session)

    async def submit_bid(self, provider: Provider, data: BidCreate) -> Bid:
        """Provider submits a price quote on an open job."""
        job = await self.job_repo.get_by_id(data.job_id)
        if not job:
            raise EntityNotFoundException("Job", data.job_id)

        if job.status not in [JobStatus.OPEN, JobStatus.BIDDING]:
            raise BadRequestException("This job is no longer accepting new bids.")

        existing = await self.bid_repo.get_by_job_and_provider(job.id, provider.id)
        if existing:
            raise ConflictException("You have already submitted a quote for this job.")

        parsed_date = parse_optional_datetime(data.proposed_start_date)

        bid = Bid(
            job_id=job.id,
            provider_id=provider.id,
            amount=data.amount,
            eta_description=data.eta_description,
            proposed_start_date=parsed_date,
            message=data.message,
            warranty_terms=data.warranty_terms,
            status=BidStatus.PENDING,
        )
        self.session.add(bid)

        # Transition job state to BIDDING if it was OPEN
        if job.status == JobStatus.OPEN:
            job.status = JobStatus.BIDDING

        await self.session.flush()
        await self.session.refresh(bid)

        # Notify customer about the new bid quote
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.session)
            await notif_service.notify_bid_received(
                customer_user_id=job.customer_id,
                provider_name=provider.business_name or "A service professional",
                amount=bid.amount,
                job_id=job.id,
                bid_id=bid.id,
            )
        except Exception:
            pass

        return bid

    async def get_bids_for_job(self, customer: User, job_id: uuid.UUID) -> List[Bid]:
        """Customer retrieves and compares all submitted quotes for their job."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise EntityNotFoundException("Job", job_id)

        if job.customer_id != customer.id:
            raise ForbiddenException("You can only view bids submitted on your own job requests.")

        return await self.bid_repo.get_bids_for_job(job_id)

    async def get_provider_bids(
        self, provider: Provider, status: Optional[BidStatus] = None
    ) -> List[Bid]:
        """Provider retrieves their submitted quotes with job context."""
        return await self.bid_repo.get_provider_bids(provider.id, status=status)

    async def update_bid(self, provider: Provider, bid_id: uuid.UUID, data: BidUpdate) -> Bid:
        """Provider updates their pending quote."""
        bid = await self.bid_repo.get_by_id(bid_id)
        if not bid:
            raise EntityNotFoundException("Bid", bid_id)

        if bid.provider_id != provider.id:
            raise ForbiddenException("You can only modify your own bids.")

        if bid.status != BidStatus.PENDING:
            raise BadRequestException("Only pending quotes can be modified.")

        if data.amount is not None:
            bid.amount = data.amount
        if data.eta_description is not None:
            bid.eta_description = data.eta_description
        if data.proposed_start_date is not None:
            bid.proposed_start_date = parse_optional_datetime(data.proposed_start_date)
        if data.message is not None:
            bid.message = data.message
        if data.warranty_terms is not None:
            bid.warranty_terms = data.warranty_terms

        self.session.add(bid)
        await self.session.flush()
        await self.session.refresh(bid)
        return bid

    async def withdraw_bid(self, provider: Provider, bid_id: uuid.UUID) -> bool:
        """Provider withdraws their pending quote."""
        bid = await self.bid_repo.get_by_id(bid_id)
        if not bid:
            raise EntityNotFoundException("Bid", bid_id)

        if bid.provider_id != provider.id:
            raise ForbiddenException("You can only withdraw your own bids.")

        if bid.status != BidStatus.PENDING:
            raise BadRequestException("Only pending bids can be withdrawn.")

        bid.status = BidStatus.WITHDRAWN
        self.session.add(bid)
        await self.session.flush()
        return True
