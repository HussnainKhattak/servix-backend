from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.bids import router as bids_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.admin import router as admin_router
from app.api.v1.feed import router as feed_router
from app.api.v1.users import router as users_router
from app.utils.response import success_response

api_router = APIRouter()

# Register All API Sub-Routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(categories_router)
api_router.include_router(jobs_router)
api_router.include_router(bids_router)
api_router.include_router(bookings_router)
api_router.include_router(reviews_router)
api_router.include_router(favorites_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_router)
api_router.include_router(feed_router)


@api_router.get("/health", tags=["Health"])
async def health_check():
    """Healthcheck endpoint for Kubernetes, Docker, and load balancers."""
    return success_response(
        data={"status": "healthy", "service": "Servix Backend API", "version": "1.0.0"},
        message="Service is running smoothly",
    )
