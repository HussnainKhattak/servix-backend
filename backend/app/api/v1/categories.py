import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_admin, get_current_provider_profile
from app.models.user import User
from app.models.provider import Provider
from app.schemas.base import ApiResponse
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services.category_service import CategoryService
from app.utils.response import success_response

router = APIRouter(prefix="/categories", tags=["Service Categories"])


@router.get("", response_model=ApiResponse[List[CategoryResponse]], summary="List Categories")
async def list_categories(session: AsyncSession = Depends(get_db)):
    """Fetch all active service categories."""
    service = CategoryService(session)
    cats = await service.list_active_categories()
    return success_response(
        data=[CategoryResponse.model_validate(c) for c in cats],
        message="Categories retrieved successfully.",
    )


@router.get("/{category_id}", response_model=ApiResponse[CategoryResponse], summary="Get Category")
async def get_category(category_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    """Retrieve details for a single category."""
    service = CategoryService(session)
    cat = await service.get_category_by_id(category_id)
    return success_response(
        data=CategoryResponse.model_validate(cat),
        message="Category retrieved successfully.",
    )


@router.post("", response_model=ApiResponse[CategoryResponse], status_code=status.HTTP_201_CREATED, summary="Create Category (Admin)")
async def create_category(
    data: CategoryCreate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin creates a new marketplace category."""
    service = CategoryService(session)
    cat = await service.create_category(data)
    return success_response(
        data=CategoryResponse.model_validate(cat),
        message=f"Category '{cat.name}' created successfully.",
    )


@router.put("/{category_id}", response_model=ApiResponse[CategoryResponse], summary="Update Category (Admin)")
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin updates an existing category."""
    service = CategoryService(session)
    cat = await service.update_category(category_id, data)
    return success_response(
        data=CategoryResponse.model_validate(cat),
        message=f"Category '{cat.name}' updated successfully.",
    )


@router.post("/{category_id}/provider-services", response_model=ApiResponse[bool], summary="Attach Service (Provider)")
async def add_provider_service(
    category_id: uuid.UUID,
    custom_hourly_rate: Optional[float] = None,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Provider adds a trade category to their offered services."""
    service = CategoryService(session)
    await service.add_provider_service(provider, category_id, custom_hourly_rate)
    return success_response(data=True, message="Service added to your provider profile.")


@router.delete("/{category_id}/provider-services", response_model=ApiResponse[bool], summary="Remove Service (Provider)")
async def remove_provider_service(
    category_id: uuid.UUID,
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Provider removes a trade category from their offered services."""
    service = CategoryService(session)
    await service.remove_provider_service(provider, category_id)
    return success_response(data=True, message="Service removed from your provider profile.")
