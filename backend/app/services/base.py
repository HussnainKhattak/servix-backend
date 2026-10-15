from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Base application service containing shared session context."""

    def __init__(self, session: AsyncSession):
        self.session = session
