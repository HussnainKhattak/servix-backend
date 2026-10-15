from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.middleware.cors import setup_cors
from app.middleware.process_time import ProcessTimeMiddleware
from app.middleware.error_handler import setup_exception_handlers
from app.api.v1.api import api_router
from app.utils.response import success_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event lifecycle manager."""
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")

    # Validate database connection
    try:
        from app.database.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to PostgreSQL database.")
    except Exception as e:
        logger.warning(f"Database connection check warning: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")
    from app.database.session import engine
    await engine.dispose()
    logger.info("Database connection pool closed.")


def create_application() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-ready asynchronous REST API backend for the Servix Local Service Marketplace.",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # 1. Setup CORS
    setup_cors(app)

    # 2. Add Process Time Header
    app.add_middleware(ProcessTimeMiddleware)

    # 3. Setup Global Exception Handlers
    setup_exception_handlers(app)

    # 4. Mount Static Files for Uploads
    import os
    from fastapi.staticfiles import StaticFiles
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # 5. Include API Routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    from app.api.v1.users import router as users_direct_router
    app.include_router(users_direct_router)

    # 6. Root Ping Endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return success_response(
            data={
                "app": settings.APP_NAME,
                "environment": settings.APP_ENV,
                "docs": "/docs" if settings.DEBUG else "Disabled in production",
            },
            message="Servix API is running.",
        )

    @app.get("/health", tags=["Root"])
    async def health():
        return success_response(
            data={"status": "UP"},
            message="System healthy",
        )

    return app


app = create_application()
