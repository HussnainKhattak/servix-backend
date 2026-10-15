import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.enums import JobStatus, UrgencyLevel
from app.schemas.user import UserPublicResponse
from app.schemas.category import CategoryResponse


class JobImageResponse(BaseModel):
    id: uuid.UUID
    image_url: str
    is_cover: bool

    model_config = ConfigDict(from_attributes=True)


class JobBase(BaseModel):
    title: str
    description: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    urgency: UrgencyLevel = UrgencyLevel.FLEXIBLE
    target_budget: Optional[float] = None
    address: str
    city: str
    state: str
    zip_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class JobCreate(JobBase):
    image_urls: Optional[List[str]] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    urgency: Optional[UrgencyLevel] = None
    target_budget: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    status: Optional[JobStatus] = None


class JobResponse(JobBase):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    bids_count: Optional[int] = 0
    lowest_bid: Optional[float] = None
    images: List[JobImageResponse] = []
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailResponse(JobResponse):
    customer: Optional[UserPublicResponse] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
