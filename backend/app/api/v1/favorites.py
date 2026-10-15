import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_active_customer
from app.models.user import User
from app.schemas.base import ApiResponse
from app.schemas.favorite import FavoriteResponse
from app.services.favorite_service import FavoriteService
from app.utils.response import success_response

router = APIRouter(prefix="/favorites", tags=["Saved Providers & Favorites"])


@router.post("/{provider_id}", response_model=ApiResponse[FavoriteResponse], status_code=status.HTTP_201_CREATED, summary="Save Favorite Provider (Customer)")
async def add_favorite(
    provider_id: uuid.UUID,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Save a top-rated service provider to customer's favorites."""
    service = FavoriteService(session)
    fav = await service.add_favorite(customer, provider_id)
    return success_response(
        data=FavoriteResponse.model_validate(fav),
        message="Provider added to favorites.",
    )


@router.delete("/{provider_id}", response_model=ApiResponse[bool], summary="Remove Favorite Provider (Customer)")
async def remove_favorite(
    provider_id: uuid.UUID,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Remove a provider from customer's favorites."""
    service = FavoriteService(session)
    await service.remove_favorite(customer, provider_id)
    return success_response(data=True, message="Provider removed from favorites.")


@router.get("", response_model=ApiResponse[List[FavoriteResponse]], summary="List Favorites (Customer)")
async def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all favorited service providers for the current customer."""
    service = FavoriteService(session)
    favorites = await service.list_favorites(customer, skip=skip, limit=limit)
    return success_response(
        data=[FavoriteResponse.model_validate(f) for f in favorites],
        message="Favorites retrieved successfully.",
    )
