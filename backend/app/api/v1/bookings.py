import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import (
    get_current_user,
    get_current_active_customer,
    get_current_provider_profile,
)
from app.models.enums import BookingStatus, UserRole
from app.models.user import User
from app.models.provider import Provider
from app.schemas.base import ApiResponse
from app.schemas.booking import BookingCreate, BookingResponse, BookingDetailResponse
from app.services.escrow_service import EscrowBookingService
from app.utils.response import success_response

router = APIRouter(prefix="/bookings", tags=["Bookings & Escrow Payments"])


class DisputeRequest(BaseModel):
    reason: str


@router.post("/accept-bid", response_model=ApiResponse[BookingDetailResponse], status_code=status.HTTP_201_CREATED, summary="Accept Bid & Lock Escrow (Customer)")
async def accept_bid_and_book(
    data: BookingCreate,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """
    Customer accepts a pro's bid quote:
    1. Locks quote amount in Escrow (HOLDING).
    2. Assigns the job to the provider.
    3. Rejects competing bids.
    4. Creates confirmed booking.
    """
    service = EscrowBookingService(session)
    booking = await service.accept_bid_and_book(customer, data)
    return success_response(
        data=BookingDetailResponse.model_validate(booking),
        message="Quote accepted! Escrow funds locked securely. Provider has been booked.",
    )


@router.get("/my-bookings", response_model=ApiResponse[List[BookingResponse]], summary="List User Bookings")
async def get_my_bookings(
    status: Optional[BookingStatus] = Query(None, description="Filter by status: CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED, DISPUTED"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all bookings relevant to the current user (Customer or Provider)."""
    service = EscrowBookingService(session)
    if current_user.role == UserRole.PROVIDER:
        from app.repositories.provider import ProviderRepository
        pro = await ProviderRepository(session).get_by_user_id(current_user.id)
        if not pro:
            bookings = []
        else:
            bookings = await service.get_provider_bookings(pro, status=status)
    else:
        bookings = await service.get_customer_bookings(current_user, status=status)

    return success_response(
        data=[BookingResponse.model_validate(b) for b in bookings],
        message="Bookings retrieved successfully.",
    )


@router.get("/{booking_id}", response_model=ApiResponse[BookingDetailResponse], summary="Get Booking Details")
async def get_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve full booking details, agreed price, escrow status, and payout breakdown."""
    service = EscrowBookingService(session)
    booking = await service.get_booking_details(booking_id)
    return success_response(
        data=BookingDetailResponse.model_validate(booking),
        message="Booking details retrieved successfully.",
    )


@router.post("/{booking_id}/start", response_model=ApiResponse[BookingDetailResponse], summary="Start Work (Provider)")
async def start_job(
    booking_id: uuid.UUID,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Service provider marks that work has commenced on site."""
    service = EscrowBookingService(session)
    booking = await service.start_job(provider, booking_id)
    return success_response(
        data=BookingDetailResponse.model_validate(booking),
        message="Job is now in progress.",
    )


@router.post("/{booking_id}/confirm-release", response_model=ApiResponse[BookingDetailResponse], summary="Confirm Completion & Release Escrow (Customer)")
async def confirm_completion_and_release(
    booking_id: uuid.UUID,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Customer confirms work completion and authorizes release of escrow funds to provider."""
    service = EscrowBookingService(session)
    booking = await service.confirm_completion_and_release_escrow(customer, booking_id)
    return success_response(
        data=BookingDetailResponse.model_validate(booking),
        message="Job marked complete! Escrow payout has been released to the service provider.",
    )


@router.post("/{booking_id}/dispute", response_model=ApiResponse[BookingDetailResponse], summary="Raise Booking Dispute")
async def raise_dispute(
    booking_id: uuid.UUID,
    data: DisputeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Customer or Provider opens a formal dispute for admin mediation."""
    service = EscrowBookingService(session)
    booking = await service.raise_dispute(current_user, booking_id, data.reason)
    return success_response(
        data=BookingDetailResponse.model_validate(booking),
        message="Dispute registered. Our support team has been notified for mediation.",
    )
