from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination query parameters."""
    page: int = Field(default=1, ge=1, description="Page number starting from 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginationMeta(BaseModel):
    """Metadata describing the pagination state."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated container response."""
    items: List[T]
    meta: PaginationMeta

    @classmethod
    def create(cls, items: List[T], total_items: int, params: PaginationParams):
        total_pages = max(1, (total_items + params.page_size - 1) // params.page_size) if total_items > 0 else 1
        meta = PaginationMeta(
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )
        return cls(items=items, meta=meta)


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard top-level API envelope format for all Servix endpoints.
    Ensures consistent front-end contract: success flag, data payload, optional error/message.
    """
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[dict]] = None

    model_config = ConfigDict(from_attributes=True)
