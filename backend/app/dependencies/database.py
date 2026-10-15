from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db

# Re-export get_db for clean dependency injection in routers
get_db_session = get_db

__all__ = ["get_db_session", "get_db"]
