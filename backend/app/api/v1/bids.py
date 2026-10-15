import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_active_customer, get_current_provider_profile
from app.models.enums import BidStatus
from app.models.user import User
from app.models.provider import Provider
from app.schemas.base import ApiResponse
from app.schemas.bid import BidCreate, BidUpdate, BidResponse, BidCompareItemResponse
from app.services.bid_service import BidService
from app.utils.response import success_response

router = APIRouter(prefix="/bids", tags=["Bids & Quotes"])


@router.post("", response_model=ApiResponse[BidResponse], status_code=status.HTTP_201_CREATED, summary="Submit Quote (Provider)")
async def submit_bid(
    data: BidCreate,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Service provider submits a price offer and ETA on an open job."""
    service = BidService(session)
    bid = await service.submit_bid(provider, data)
    return success_response(
        data=BidResponse.model_validate(bid),
        message="Quote submitted successfully.",
    )


@router.get("/my-bids", response_model=ApiResponse[List[BidResponse]], summary="List Provider Bids")
async def get_my_bids(
    status: Optional[BidStatus] = Query(None, description="Filter by status: PENDING, ACCEPTED, REJECTED, WITHDRAWN"),
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Provider retrieves all bids they have submitted across the platform."""
    service = BidService(session)
    bids = await service.get_provider_bids(provider, status=status)
    return success_response(
        data=[BidResponse.model_validate(b) for b in bids],
        message="Provider bids retrieved successfully.",
    )


@router.get("/job/{job_id}", response_model=ApiResponse[List[BidResponse]], summary="Compare Job Quotes (Customer)")
async def get_job_bids(
    job_id: uuid.UUID,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Customer compares all price offers, provider ratings, and ETAs received for a job."""
    service = BidService(session)
    bids = await service.get_bids_for_job(customer, job_id)
    return success_response(
        data=[BidResponse.model_validate(b) for b in bids],
        message="Job quotes retrieved successfully.",
    )


@router.put("/{bid_id}", response_model=ApiResponse[BidResponse], summary="Update Quote (Provider)")
async def update_bid(
    bid_id: uuid.UUID,
    data: BidUpdate,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Provider updates their price or message on a pending quote."""
    service = BidService(session)
    bid = await service.update_bid(provider, bid_id, data)
    return success_response(
        data=BidResponse.model_validate(bid),
        message="Quote updated successfully.",
    )


@router.delete("/{bid_id}/withdraw", response_model=ApiResponse[bool], summary="Withdraw Quote (Provider)")
async def withdraw_bid(
    bid_id: uuid.UUID,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Provider withdraws their quote before customer acceptance."""
    service = BidService(session)
    await service.withdraw_bid(provider, bid_id)
    return success_response(data=True, message="Quote withdrawn successfully.")
