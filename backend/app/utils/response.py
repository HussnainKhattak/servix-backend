from typing import Any, List, Optional
from app.schemas.base import ApiResponse, PaginatedResponse, PaginationParams


def success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
) -> ApiResponse[Any]:
    """Helper to construct a standardized successful ApiResponse."""
    return ApiResponse(
        success=True,
        message=message,
        data=data,
        errors=None,
    )


def paginated_response(
    items: List[Any],
    total_items: int,
    params: PaginationParams,
    message: str = "Records retrieved successfully",
) -> ApiResponse[PaginatedResponse[Any]]:
    """Helper to construct a standardized paginated ApiResponse."""
    paginated_data = PaginatedResponse.create(items, total_items, params)
    return ApiResponse(
        success=True,
        message=message,
        data=paginated_data,
        errors=None,
    )


def error_response(
    message: str,
    errors: Optional[List[dict]] = None,
) -> ApiResponse[Any]:
    """Helper to construct a standardized error ApiResponse."""
    return ApiResponse(
        success=False,
        message=message,
        data=None,
        errors=errors,
    )
