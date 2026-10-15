import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.base import ApiResponse
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService
from app.utils.response import success_response

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=ApiResponse[List[NotificationResponse]], summary="Get User Notifications")
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetch recent in-app notifications for the authenticated user."""
    service = NotificationService(session)
    notifs = await service.get_user_notifications(current_user.id, skip=skip, limit=limit)
    return success_response(
        data=[NotificationResponse.model_validate(n) for n in notifs],
        message="Notifications retrieved successfully.",
    )


@router.get("/unread-count", response_model=ApiResponse[Dict[str, int]], summary="Get Unread Notification Count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve the total count of unread notifications for badge display."""
    service = NotificationService(session)
    count = await service.get_unread_count(current_user.id)
    return success_response(data={"unread_count": count}, message="Unread count retrieved.")


@router.post("/{notification_id}/read", response_model=ApiResponse[bool], summary="Mark Notification as Read")
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Mark a specific notification as read."""
    service = NotificationService(session)
    success = await service.mark_as_read(current_user.id, notification_id)
    return success_response(data=success, message="Notification marked as read.")


@router.post("/read-all", response_model=ApiResponse[int], summary="Mark All Notifications as Read")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for current user."""
    service = NotificationService(session)
    count = await service.mark_all_as_read(current_user.id)
    return success_response(data=count, message=f"{count} notifications marked as read.")
