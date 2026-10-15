import uuid
from typing import List, Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.database.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.models.provider import Provider
from app.repositories.user import UserRepository
from app.repositories.provider import ProviderRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user if valid token provided; otherwise None without raising."""
    if not token:
        return None

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the currently authenticated user from Bearer JWT."""
    if not token:
        raise UnauthorizedException("Authentication token is required.")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedException("Invalid or expired authentication token.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token subject.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Malformed user identifier.")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedException("User account not found or inactive.")

    return user


async def get_current_active_customer(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure current user is an active customer."""
    if current_user.role not in [UserRole.CUSTOMER, UserRole.ADMIN]:
        raise ForbiddenException("Only customers can perform this action.")
    return current_user


async def get_current_provider_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Provider:
    """Ensure current user is a service provider and return their verified profile."""
    if current_user.role not in [UserRole.PROVIDER, UserRole.ADMIN]:
        raise ForbiddenException("Only service providers can perform this action.")

    provider_repo = ProviderRepository(session)
    provider = await provider_repo.get_by_user_id(current_user.id)
    if not provider:
        raise ForbiddenException("Service provider profile has not been initialized.")

    return provider


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure current user is a platform administrator."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Administrator privileges required.")
    return current_user


def require_roles(allowed_roles: List[UserRole]):
    """Role-based access control (RBAC) dependency factory."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException("You do not have the required role permissions.")
        return current_user
    return role_checker
