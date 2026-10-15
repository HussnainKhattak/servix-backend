import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserPublicResponse


class ProviderBase(BaseModel):
    business_name: str
    trade: str
    license_number: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    service_radius_miles: float = 15.0
    experience_years: int = 1
    is_available: bool = True
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class ProviderCreate(ProviderBase):
    user_id: uuid.UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProviderUpdate(BaseModel):
    business_name: Optional[str] = None
    trade: Optional[str] = None
    license_number: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    service_radius_miles: Optional[float] = None
    experience_years: Optional[int] = None
    is_available: Optional[bool] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProviderResponse(ProviderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_license_verified: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    avg_rating: float
    reviews_count: int
    jobs_completed: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserPublicResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderPublicCardResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    business_name: str
    trade: str
    avg_rating: float
    reviews_count: int
    jobs_completed: int
    hourly_rate: Optional[float] = None
    location: str
    distance_miles: Optional[float] = None
    is_license_verified: bool
    is_available: bool
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
