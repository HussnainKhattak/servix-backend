import os
import uuid
import aiofiles
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BadRequestException
from app.dependencies.database import get_db
from sqlalchemy import select
from app.dependencies.auth import get_current_user, get_current_user_optional, get_current_active_customer, get_current_provider_profile
from app.models.enums import JobStatus, UserRole
from app.models.user import User
from app.models.provider import Provider
from app.schemas.base import ApiResponse
from app.schemas.job import JobCreate, JobResponse, JobDetailResponse, JobImageResponse
from app.services.job_service import JobService
from app.utils.response import success_response

router = APIRouter(prefix="/jobs", tags=["Jobs & Service Requests"])


@router.post("", response_model=ApiResponse[JobDetailResponse], status_code=status.HTTP_201_CREATED, summary="Create Job Request (Customer)")
async def create_job(
    data: JobCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_db),
):
    """Customer posts a new service job broadcast to nearby professionals."""
    if current_user and current_user.role in [UserRole.CUSTOMER, UserRole.ADMIN]:
        customer = current_user
    else:
        # Resolve to an active customer in the system for guest/demo posts
        res = await session.execute(
            select(User)
            .where(User.role == UserRole.CUSTOMER, User.is_active == True)
            .order_by(User.created_at.asc())
        )
        customer = res.scalars().first()
        if not customer:
            # Fallback to any active user
            res_any = await session.execute(select(User).where(User.is_active == True).limit(1))
            customer = res_any.scalars().first()

    service = JobService(session)
    job = await service.create_job(customer, data)
    return success_response(
        data=JobDetailResponse.model_validate(job),
        message="Service request posted successfully. Nearby pros will be notified.",
    )


@router.get("/my-jobs", response_model=ApiResponse[List[JobResponse]], summary="List Customer Jobs")
async def get_my_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by status: OPEN, BIDDING, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Customer retrieves all jobs they have posted."""
    service = JobService(session)
    jobs = await service.get_customer_jobs(customer, status=status, skip=skip, limit=limit)
    return success_response(
        data=[JobResponse.model_validate(j) for j in jobs],
        message="Customer jobs retrieved successfully.",
    )


@router.get("/nearby", response_model=ApiResponse[List[JobResponse]], summary="Browse Nearby Jobs (Provider)")
async def get_nearby_jobs(
    category_id: Optional[uuid.UUID] = Query(None),
    max_distance_miles: Optional[float] = Query(None, description="Max distance from provider in miles"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    provider: Provider = Depends(get_current_provider_profile),
    session: AsyncSession = Depends(get_db),
):
    """Provider browses open jobs within their operating radius."""
    service = JobService(session)
    jobs_with_distance = await service.get_nearby_jobs_for_provider(
        provider, category_id=category_id, max_distance_miles=max_distance_miles, skip=skip, limit=limit
    )
    return success_response(
        data=[JobResponse.model_validate(item[0]) for item in jobs_with_distance],
        message="Nearby jobs retrieved successfully.",
    )


@router.get("/{job_id}", response_model=ApiResponse[JobDetailResponse], summary="Get Job Details")
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve full job details, photo attachments, category, and submitted quotes."""
    service = JobService(session)
    job = await service.get_job_details(job_id)
    return success_response(
        data=JobDetailResponse.model_validate(job),
        message="Job details retrieved successfully.",
    )


@router.delete("/{job_id}/cancel", response_model=ApiResponse[JobResponse], summary="Cancel Job (Customer)")
async def cancel_job(
    job_id: uuid.UUID,
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Customer cancels an open or bidding service request."""
    service = JobService(session)
    job = await service.cancel_job(customer, job_id)
    return success_response(
        data=JobResponse.model_validate(job),
        message="Job cancelled successfully.",
    )


@router.post("/{job_id}/images", response_model=ApiResponse[List[str]], summary="Upload Job Photos")
async def upload_job_images(
    job_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    customer: User = Depends(get_current_active_customer),
    session: AsyncSession = Depends(get_db),
):
    """Upload photos depicting the problem / job site (JPEG, PNG, WebP)."""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    uploads_dir = os.path.join(os.getcwd(), "uploads", "jobs", str(job_id))
    os.makedirs(uploads_dir, exist_ok=True)

    saved_urls: List[str] = []
    for file in files:
        if file.content_type not in allowed_types:
            continue
        ext = os.path.splitext(file.filename or "")[1] or ".jpg"
        filename = f"{uuid.uuid4().hex[:12]}{ext}"
        filepath = os.path.join(uploads_dir, filename)

        content = await file.read()
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(content)

        saved_urls.append(f"/uploads/jobs/{job_id}/{filename}")

    if not saved_urls:
        raise BadRequestException("No valid image files were provided.")

    service = JobService(session)
    await service.add_job_images(job_id, saved_urls)
    return success_response(data=saved_urls, message="Job images uploaded successfully.")
