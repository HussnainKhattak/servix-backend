import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import BookingStatus, EscrowStatus
from app.schemas.user import UserPublicResponse
from app.schemas.provider import ProviderResponse


class BookingCreate(BaseModel):
    job_id: uuid.UUID
    bid_id: uuid.UUID
    scheduled_date: str
    scheduled_time: str


class BookingResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    bid_id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    agreed_price: float
    platform_fee: float
    provider_payout: float
    status: BookingStatus
    escrow_status: EscrowStatus
    scheduled_date: str
    scheduled_time: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingDetailResponse(BookingResponse):
    customer: Optional[UserPublicResponse] = None
    provider: Optional[ProviderResponse] = None
    job_title: Optional[str] = None
    service_category: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
