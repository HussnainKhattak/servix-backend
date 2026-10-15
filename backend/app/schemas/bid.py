import uuid
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import BidStatus
from app.schemas.provider import ProviderResponse, ProviderPublicCardResponse


class BidBase(BaseModel):
    amount: float = Field(gt=0, description="Proposed fixed quote amount")
    eta_description: str
    proposed_start_date: Optional[Union[datetime, str]] = None
    message: str = Field(min_length=5)
    warranty_terms: Optional[str] = None


class BidCreate(BidBase):
    job_id: uuid.UUID


class BidUpdate(BaseModel):
    amount: Optional[float] = None
    eta_description: Optional[str] = None
    proposed_start_date: Optional[Union[datetime, str]] = None
    message: Optional[str] = None
    warranty_terms: Optional[str] = None


class BidResponse(BidBase):
    id: uuid.UUID
    job_id: uuid.UUID
    provider_id: uuid.UUID
    status: BidStatus
    created_at: datetime
    updated_at: datetime
    provider: Optional[ProviderResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BidCompareItemResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    business_name: str
    rating: float
    reviews_count: int
    jobs_completed: int
    amount: float
    eta: str
    distance: str
    message: str
    warranty: Optional[str] = None
    is_lowest_price: bool = False
    is_fastest_eta: bool = False

    model_config = ConfigDict(from_attributes=True)
