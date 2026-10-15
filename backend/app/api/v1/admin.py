import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.enums import UserRole, JobStatus
from app.models.user import User
from app.schemas.base import ApiResponse
from app.schemas.user import UserResponse
from app.schemas.category import CategoryResponse
from app.schemas.admin import (
    AdminUserResponse,
    AdminProviderResponse,
    AdminJobResponse,
    AdminCategoryCreate,
    AdminCategoryUpdate,
    AdminReviewResponse,
    AdminReportsResponse,
)
from app.services.admin_service import AdminService
from app.utils.response import success_response

router = APIRouter(prefix="/admin", tags=["Admin Platform Management"])


class UserStatusUpdate(BaseModel):
    is_active: bool


class ProviderVerificationUpdate(BaseModel):
    is_verified: bool


class AdminJobCancelRequest(BaseModel):
    reason: Optional[str] = None


class AdminReviewFlagRequest(BaseModel):
    reason: str


# ─────────────────────────────────────────────────────────
# DASHBOARD & REPORTS
# ─────────────────────────────────────────────────────────

@router.get("/metrics", response_model=ApiResponse[Dict[str, Any]], summary="Dashboard Statistics (Admin)")
async def get_metrics(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve aggregate platform analytics (users, providers, active/completed jobs, escrow volume, platform revenue)."""
    service = AdminService(session)
    metrics = await service.get_dashboard_metrics()
    return success_response(data=metrics, message="Admin dashboard metrics retrieved.")


@router.get("/reports", response_model=ApiResponse[AdminReportsResponse], summary="Platform Reports (Admin)")
async def get_reports(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve comprehensive platform health and operational reports."""
    service = AdminService(session)
    reports = await service.get_reports()
    return success_response(data=AdminReportsResponse(**reports), message="Platform reports generated.")


# ─────────────────────────────────────────────────────────
# USER MANAGEMENT & ACCOUNT SUSPENSION
# ─────────────────────────────────────────────────────────

@router.get("/users", response_model=ApiResponse[List[AdminUserResponse]], summary="Manage Users (Admin)")
async def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by CUSTOMER, PROVIDER, ADMIN"),
    is_active: Optional[bool] = Query(None, description="Filter by active vs suspended"),
    search: Optional[str] = Query(None, description="Search name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: list all registered platform users with search and role filters."""
    service = AdminService(session)
    users = await service.list_users(role=role, is_active=is_active, search=search, skip=skip, limit=limit)
    return success_response(
        data=[AdminUserResponse.model_validate(u) for u in users],
        message="Users list retrieved.",
    )


@router.get("/users/{user_id}", response_model=ApiResponse[AdminUserResponse], summary="Get User Details (Admin)")
async def get_user(
    user_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: retrieve detailed profile of any registered user."""
    service = AdminService(session)
    user = await service.get_user_details(user_id)
    return success_response(data=AdminUserResponse.model_validate(user), message="User details retrieved.")


@router.post("/users/{user_id}/status", response_model=ApiResponse[AdminUserResponse], summary="Suspend / Restore User (Admin)")
async def update_user_status(
    user_id: uuid.UUID,
    data: UserStatusUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin suspends or restores a user account."""
    service = AdminService(session)
    user = await service.set_user_active_status(user_id, data.is_active)
    status_str = "restored" if data.is_active else "suspended"
    return success_response(
        data=AdminUserResponse.model_validate(user),
        message=f"User account has been {status_str}.",
    )


# ─────────────────────────────────────────────────────────
# PROVIDER MANAGEMENT & VERIFICATION
# ─────────────────────────────────────────────────────────

@router.get("/providers", response_model=ApiResponse[List[AdminProviderResponse]], summary="Manage Providers (Admin)")
async def list_providers(
    is_verified: Optional[bool] = Query(None, description="Filter by verified license"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    trade: Optional[str] = Query(None, description="Filter by trade name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: list service professionals with verification and trade filters."""
    service = AdminService(session)
    providers = await service.list_providers(
        is_verified=is_verified, is_available=is_available, trade=trade, skip=skip, limit=limit
    )
    result = []
    for p in providers:
        item = AdminProviderResponse(
            id=p.id,
            user_id=p.user_id,
            business_name=p.business_name,
            trade=p.trade,
            is_license_verified=p.is_license_verified,
            is_available=p.is_available,
            avg_rating=p.avg_rating,
            reviews_count=p.reviews_count,
            jobs_completed=p.jobs_completed,
            city=p.city,
            state=p.state,
            created_at=p.created_at,
            email=p.user.email if p.user else None,
            full_name=p.user.full_name if p.user else None,
            is_active=p.user.is_active if p.user else None,
        )
        result.append(item)
    return success_response(data=result, message="Providers list retrieved.")


@router.get("/providers/{provider_id}", response_model=ApiResponse[AdminProviderResponse], summary="Get Provider Details (Admin)")
async def get_provider(
    provider_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: retrieve detailed provider business and license information."""
    service = AdminService(session)
    p = await service.get_provider_details(provider_id)
    item = AdminProviderResponse(
        id=p.id,
        user_id=p.user_id,
        business_name=p.business_name,
        trade=p.trade,
        is_license_verified=p.is_license_verified,
        is_available=p.is_available,
        avg_rating=p.avg_rating,
        reviews_count=p.reviews_count,
        jobs_completed=p.jobs_completed,
        city=p.city,
        state=p.state,
        created_at=p.created_at,
        email=p.user.email if p.user else None,
        full_name=p.user.full_name if p.user else None,
        is_active=p.user.is_active if p.user else None,
    )
    return success_response(data=item, message="Provider details retrieved.")


@router.post("/providers/{provider_id}/verify", response_model=ApiResponse[AdminProviderResponse], summary="Verify Provider (Admin)")
async def verify_provider(
    provider_id: uuid.UUID,
    data: ProviderVerificationUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin approves and verifies a service professional's trade license and credentials."""
    service = AdminService(session)
    p = await service.set_provider_verification(provider_id, data.is_verified)
    item = AdminProviderResponse(
        id=p.id,
        user_id=p.user_id,
        business_name=p.business_name,
        trade=p.trade,
        is_license_verified=p.is_license_verified,
        is_available=p.is_available,
        avg_rating=p.avg_rating,
        reviews_count=p.reviews_count,
        jobs_completed=p.jobs_completed,
        city=p.city,
        state=p.state,
        created_at=p.created_at,
        email=p.user.email if p.user else None,
        full_name=p.user.full_name if p.user else None,
        is_active=p.user.is_active if p.user else None,
    )
    status_str = "verified" if data.is_verified else "unverified"
    return success_response(data=item, message=f"Provider has been marked as {status_str}.")


# ─────────────────────────────────────────────────────────
# CATEGORY MANAGEMENT
# ─────────────────────────────────────────────────────────

@router.get("/categories", response_model=ApiResponse[List[CategoryResponse]], summary="Manage Categories (Admin)")
async def list_categories(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: list all categories (active and inactive)."""
    service = AdminService(session)
    categories = await service.list_categories()
    return success_response(
        data=[CategoryResponse.model_validate(c) for c in categories],
        message="Categories list retrieved.",
    )


@router.post("/categories", response_model=ApiResponse[CategoryResponse], status_code=status.HTTP_201_CREATED, summary="Create Category (Admin)")
async def create_category(
    data: AdminCategoryCreate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: create a new marketplace trade category."""
    service = AdminService(session)
    cat = await service.create_category(data)
    return success_response(
        data=CategoryResponse.model_validate(cat),
        message="Category created successfully.",
    )


@router.put("/categories/{category_id}", response_model=ApiResponse[CategoryResponse], summary="Update Category (Admin)")
async def update_category(
    category_id: uuid.UUID,
    data: AdminCategoryUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: update category name, slug, description, or active status."""
    service = AdminService(session)
    cat = await service.update_category(category_id, data)
    return success_response(
        data=CategoryResponse.model_validate(cat),
        message="Category updated successfully.",
    )


@router.delete("/categories/{category_id}", response_model=ApiResponse[bool], summary="Delete/Deactivate Category (Admin)")
async def delete_category(
    category_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: deactivate a service category."""
    service = AdminService(session)
    await service.delete_category(category_id)
    return success_response(data=True, message="Category deactivated.")


# ─────────────────────────────────────────────────────────
# JOB MODERATION
# ─────────────────────────────────────────────────────────

@router.get("/jobs", response_model=ApiResponse[List[AdminJobResponse]], summary="Manage Jobs (Admin)")
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: monitor and moderate all job requests across the platform."""
    service = AdminService(session)
    jobs = await service.list_jobs(status=status, category_id=category_id, skip=skip, limit=limit)
    result = [
        AdminJobResponse(
            id=j.id,
            title=j.title,
            status=j.status,
            customer_id=j.customer_id,
            category_id=j.category_id,
            city=j.city,
            state=j.state,
            target_budget=j.target_budget,
            created_at=j.created_at,
            customer_name=j.customer.full_name if j.customer else None,
        )
        for j in jobs
    ]
    return success_response(data=result, message="Jobs list retrieved.")


@router.post("/jobs/{job_id}/cancel", response_model=ApiResponse[AdminJobResponse], summary="Force Cancel Job (Admin)")
async def cancel_job(
    job_id: uuid.UUID,
    data: AdminJobCancelRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin force-cancels a job in dispute or non-compliance."""
    service = AdminService(session)
    job = await service.cancel_job_admin(job_id, reason=data.reason)
    return success_response(
        data=AdminJobResponse(
            id=job.id,
            title=job.title,
            status=job.status,
            customer_id=job.customer_id,
            category_id=job.category_id,
            city=job.city,
            state=job.state,
            target_budget=job.target_budget,
            created_at=job.created_at,
            customer_name=job.customer.full_name if job.customer else None,
        ),
        message="Job cancelled by admin.",
    )


# ─────────────────────────────────────────────────────────
# REVIEW MODERATION
# ─────────────────────────────────────────────────────────

@router.get("/reviews", response_model=ApiResponse[List[AdminReviewResponse]], summary="Moderate Reviews (Admin)")
async def list_reviews(
    is_flagged: Optional[bool] = Query(None, description="Filter by flagged status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin: view and moderate customer reviews across the platform."""
    service = AdminService(session)
    reviews = await service.list_reviews(is_flagged=is_flagged, skip=skip, limit=limit)
    return success_response(
        data=[AdminReviewResponse.model_validate(r) for r in reviews],
        message="Reviews list retrieved.",
    )


@router.post("/reviews/{review_id}/flag", response_model=ApiResponse[AdminReviewResponse], summary="Flag Review (Admin)")
async def flag_review(
    review_id: uuid.UUID,
    data: AdminReviewFlagRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin manually flags a review for moderation."""
    service = AdminService(session)
    review = await service.flag_review(review_id, data.reason)
    return success_response(
        data=AdminReviewResponse.model_validate(review),
        message="Review flagged for investigation.",
    )


@router.delete("/reviews/{review_id}", response_model=ApiResponse[bool], summary="Remove Review (Admin)")
async def delete_review(
    review_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin unpublishes / removes an abusive review."""
    service = AdminService(session)
    await service.delete_review(review_id)
    return success_response(data=True, message="Review removed.")
