import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import (
    get_current_user,
    get_current_active_customer,
    get_current_provider_profile,
    get_current_admin,
)
from app.models.user import User
from app.models.provider import Provider
from app.schemas.base import ApiResponse
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ProviderReplyCreate,
    ReviewFlagCreate,
)
from app.services.review_service import ReviewService
from app.utils.response import success_response

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])


@router.post("", response_model=ApiResponse[ReviewResponse], status_code=status.HTTP_201_CREATED, summary="Submit Review (Customer)")
async def submit_review(
    data: ReviewCreate,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Customer submits a review and rating for a completed booking."""
    service = ReviewService(session)
    review = await service.submit_review(customer, data)
    return success_response(
        data=ReviewResponse.model_validate(review),
        message="Review submitted successfully. Thank you for your feedback!",
    )


@router.post("/{review_id}/reply", response_model=ApiResponse[ReviewResponse], summary="Provider Reply to Review")
async def reply_to_review(
    review_id: uuid.UUID,
    data: ProviderReplyCreate,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Service provider posts a public response to a client review."""
    service = ReviewService(session)
    review = await service.provider_reply_to_review(provider, review_id, data.reply_text)
    return success_response(
        data=ReviewResponse.model_validate(review),
        message="Your response has been published.",
    )


@router.post("/{review_id}/flag", response_model=ApiResponse[ReviewResponse], summary="Flag Review for Moderation")
async def flag_review(
    review_id: uuid.UUID,
    data: ReviewFlagCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Report an inappropriate or misleading review for admin moderation."""
    service = ReviewService(session)
    review = await service.flag_review(review_id, data.reason)
    return success_response(
        data=ReviewResponse.model_validate(review),
        message="Review has been flagged for admin review.",
    )


@router.get("/provider/{provider_id}", response_model=ApiResponse[List[ReviewResponse]], summary="List Provider Reviews")
async def get_provider_reviews(
    provider_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all published reviews and ratings for a service provider."""
    service = ReviewService(session)
    reviews = await service.get_provider_reviews(provider_id, skip=skip, limit=limit)
    return success_response(
        data=[ReviewResponse.model_validate(r) for r in reviews],
        message="Provider reviews retrieved successfully.",
    )


@router.delete("/{review_id}", response_model=ApiResponse[bool], summary="Delete/Unpublish Review (Admin)")
async def delete_review(
    review_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin unpublishes an abusive or policy-violating review."""
    service = ReviewService(session)
    await service.delete_review(review_id)
    return success_response(data=True, message="Review has been removed.")
