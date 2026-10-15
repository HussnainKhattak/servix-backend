import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.models.enums import JobStatus
from app.schemas.base import ApiResponse
from app.schemas.job import JobDetailResponse
from app.repositories.job import JobRepository
from app.utils.response import success_response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.job import Job

router = APIRouter(prefix="/feed", tags=["Public Feed"])


@router.get(
    "/jobs",
    response_model=ApiResponse[List[JobDetailResponse]],
    summary="Public Job Feed (No Auth Required)",
)
async def get_public_job_feed(
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category UUID"),
    city: Optional[str] = Query(None, description="Filter by city name (partial match)"),
    search: Optional[str] = Query(None, description="Search in title or description"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    session: AsyncSession = Depends(get_db),
):
    """
    Public marketplace feed — returns OPEN/BIDDING jobs ordered newest-first.
    No authentication required. Suitable for the homepage Latest Requests section.
    """
    query = (
        select(Job)
        .where(Job.status.in_([JobStatus.OPEN, JobStatus.BIDDING]))
        .options(
            selectinload(Job.category),
            selectinload(Job.customer),
            selectinload(Job.images),
            selectinload(Job.bids),
        )
        .order_by(Job.created_at.desc())
    )

    cat_id = category_id if isinstance(category_id, uuid.UUID) else None
    city_str = city if isinstance(city, str) else None
    search_str = search if isinstance(search, str) else None

    if cat_id:
        query = query.where(Job.category_id == cat_id)

    if city_str:
        query = query.where(Job.city.ilike(f"%{city_str}%"))

    if search_str:
        search_term = f"%{search_str}%"
        query = query.where(
            Job.title.ilike(search_term) | Job.description.ilike(search_term)
        )

    offset_val = skip if isinstance(skip, int) else 0
    limit_val = limit if isinstance(limit, int) else 20
    query = query.offset(offset_val).limit(limit_val)
    result = await session.execute(query)
    jobs = list(result.scalars().all())

    return success_response(
        data=[JobDetailResponse.model_validate(j) for j in jobs],
        message=f"{len(jobs)} job(s) found.",
    )
