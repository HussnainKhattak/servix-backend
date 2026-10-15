import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import UserPublicResponse


class ReviewCreate(BaseModel):
    booking_id: uuid.UUID
    rating: int = Field(ge=1, le=5, description="Star rating from 1 to 5")
    comment: str = Field(min_length=5, max_length=1000)


class ProviderReplyCreate(BaseModel):
    reply_text: str = Field(min_length=5, max_length=1000, description="Provider's public reply to the review")


class ReviewFlagCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=500, description="Reason for flagging the review")


class ReviewResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    rating: int
    comment: str
    is_flagged: bool
    is_published: bool
    flag_reason: Optional[str] = None
    provider_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    created_at: datetime
    customer: Optional[UserPublicResponse] = None

    model_config = ConfigDict(from_attributes=True)
