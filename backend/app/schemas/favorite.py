import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.provider import ProviderResponse


class FavoriteCreate(BaseModel):
    provider_id: uuid.UUID


class FavoriteResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    created_at: datetime
    provider: Optional[ProviderResponse] = None

    model_config = ConfigDict(from_attributes=True)
