import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.enums import UserRole, JobStatus, BookingStatus


class AdminUserResponse(BaseModel):
    """Lightweight user summary for admin list views."""
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    city: Optional[str] = None
    state: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminProviderResponse(BaseModel):
    """Provider summary with embedded user info for admin management."""
    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    trade: str
    is_license_verified: bool
    is_available: bool
    avg_rating: float
    reviews_count: int
    jobs_completed: int
    city: Optional[str] = None
    state: Optional[str] = None
    created_at: datetime
    # Embedded user fields
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class AdminJobResponse(BaseModel):
    """Job summary for admin moderation view."""
    id: uuid.UUID
    title: str
    status: JobStatus
    customer_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    city: Optional[str] = None
    state: Optional[str] = None
    target_budget: Optional[float] = None
    created_at: datetime
    # Embedded customer name for display
    customer_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminCategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = "🔧"
    avg_price_min: Optional[float] = None
    avg_price_max: Optional[float] = None
    is_active: bool = True


class AdminCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    avg_price_min: Optional[float] = None
    avg_price_max: Optional[float] = None
    is_active: Optional[bool] = None


class AdminReviewResponse(BaseModel):
    """Review for admin moderation list."""
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    rating: int
    comment: str
    is_flagged: bool
    flag_reason: Optional[str] = None
    is_published: bool
    provider_reply: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminReportsResponse(BaseModel):
    """Platform-wide report data for admin dashboard."""
    total_users: int
    total_providers: int
    total_jobs: int
    open_jobs: int
    active_jobs: int
    completed_jobs: int
    cancelled_jobs: int
    disputed_jobs: int
    total_bookings: int
    total_escrow_volume: float
    total_platform_revenue: float
    total_reviews: int
    avg_platform_rating: float
    verified_providers: int
    suspended_users: int
