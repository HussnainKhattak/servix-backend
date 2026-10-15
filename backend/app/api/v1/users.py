from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.base import ApiResponse
from app.utils.response import success_response

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Get Current User Profile",
)
async def get_current_user_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve the authenticated user's real profile data from the database."""
    service = AuthService(session)
    user_with_profile = await service.get_current_user_profile(current_user.id)

    role_val = (
        user_with_profile.role.value
        if hasattr(user_with_profile.role, "value")
        else str(user_with_profile.role)
    )
    joined_date = (
        user_with_profile.created_at.strftime("%b %d, %Y")
        if user_with_profile.created_at
        else ""
    )

    user_data = {
        "id": str(user_with_profile.id),
        "name": user_with_profile.full_name,
        "full_name": user_with_profile.full_name,
        "email": user_with_profile.email,
        "phone": user_with_profile.phone,
        "city": user_with_profile.city,
        "state": user_with_profile.state,
        "zip_code": user_with_profile.zip_code,
        "default_address": user_with_profile.default_address,
        "role": role_val,
        "is_active": user_with_profile.is_active,
        "is_verified": user_with_profile.is_verified,
        "avatar_url": user_with_profile.avatar_url,
        "joined_date": joined_date,
        "created_at": (
            user_with_profile.created_at.isoformat()
            if user_with_profile.created_at
            else None
        ),
        "updated_at": (
            user_with_profile.updated_at.isoformat()
            if user_with_profile.updated_at
            else None
        ),
    }

    if user_with_profile.provider_profile:
        pro = user_with_profile.provider_profile
        user_data["provider_profile"] = {
            "id": str(pro.id),
            "business_name": pro.business_name,
            "trade": pro.trade.value if hasattr(pro.trade, "value") else str(pro.trade),
            "bio": pro.bio,
            "license_number": pro.license_number,
            "hourly_rate": pro.hourly_rate,
            "service_radius_miles": pro.service_radius_miles,
            "is_available": pro.is_available,
            "rating": pro.rating,
            "review_count": pro.review_count,
        }

    return success_response(
        data=user_data,
        message="User profile retrieved successfully.",
    )
