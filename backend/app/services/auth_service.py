import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    create_email_verification_token,
    decode_token,
)
from app.core.exceptions import (
    UnauthorizedException,
    ConflictException,
    EntityNotFoundException,
    BadRequestException,
)
from app.core.logging import logger
from app.models.enums import UserRole
from app.models.user import User
from app.models.provider import Provider
from app.models.refresh_token import RefreshToken
from app.repositories.user import UserRepository
from app.repositories.provider import ProviderRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterCustomerRequest,
    RegisterProviderRequest,
    ProfileUpdateRequest,
    TokenResponse,
)
from app.services.base import BaseService


class AuthService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.refresh_token_repo = RefreshTokenRepository(session)

    async def _issue_token_pair(self, user: User) -> TokenResponse:
        """Helper to create and persist access and refresh token pair."""
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token_str = create_refresh_token(subject=user.id)

        # Store refresh token in database for tracking & revocation
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.session.add(db_token)
        await self.session.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=str(user.id),
            role=user.role,
        )

    async def authenticate(self, req: LoginRequest) -> TokenResponse:
        """Authenticate user with email and password and issue tokens.

        Role is read from the user's database record — the client does not
        send a role at login.  The issued JWT encodes the persisted role.
        """
        user = await self.user_repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedException("Account has been suspended. Please contact support.")

        # Role is always taken from the DB — no client-supplied role check.
        return await self._issue_token_pair(user)

    async def register_customer(self, req: RegisterCustomerRequest) -> Tuple[User, TokenResponse]:
        """Register a new customer, generate verification token, and log in."""
        existing = await self.user_repo.get_by_email(req.email)
        if existing:
            raise ConflictException(
                "An account with this email already exists. Please log in instead."
            )

        user = User(
            email=req.email.lower().strip(),
            hashed_password=get_password_hash(req.password),
            full_name=req.full_name.strip(),
            phone=req.phone,
            city=req.city,
            state=req.state,
            zip_code=req.zip_code,
            default_address=req.default_address,
            role=UserRole.CUSTOMER,
            is_active=True,
            is_verified=False,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        tokens = await self._issue_token_pair(user)
        verification_token = create_email_verification_token(user.email)
        logger.info(f"Generated email verification token for {user.email}: {verification_token[:20]}...")

        return user, tokens

    async def register_provider(self, req: RegisterProviderRequest) -> Tuple[User, TokenResponse]:
        """Register a new service professional and their provider profile."""
        existing = await self.user_repo.get_by_email(req.email)
        if existing:
            raise ConflictException(
                "An account with this email already exists. Please log in instead."
            )

        user = User(
            email=req.email.lower().strip(),
            hashed_password=get_password_hash(req.password),
            full_name=req.full_name.strip(),
            phone=req.phone,
            city=req.city,
            state=req.state,
            zip_code=req.zip_code,
            role=UserRole.PROVIDER,
            is_active=True,
            is_verified=False,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        provider = Provider(
            user_id=user.id,
            business_name=req.business_name.strip(),
            trade=req.trade.strip(),
            license_number=req.license_number,
            city=req.city,
            state=req.state,
            zip_code=req.zip_code,
            hourly_rate=req.hourly_rate,
            service_radius_miles=req.service_radius_miles,
            is_available=True,
            is_license_verified=False,
        )
        self.session.add(provider)
        await self.session.flush()
        await self.session.refresh(provider)

        tokens = await self._issue_token_pair(user)
        verification_token = create_email_verification_token(user.email)
        logger.info(f"Generated email verification token for pro {user.email}: {verification_token[:20]}...")

        return user, tokens

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        """Validate an active refresh token, rotate it, and issue a new token pair."""
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid or expired refresh token.")

        db_token = await self.refresh_token_repo.get_active_token(refresh_token_str)
        if not db_token:
            raise UnauthorizedException("Refresh token has been revoked or expired.")

        user = await self.user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User account not found or deactivated.")

        # Revoke the old refresh token (rotation policy)
        db_token.is_revoked = True
        self.session.add(db_token)
        await self.session.flush()

        # Issue new token pair
        return await self._issue_token_pair(user)

    async def logout(self, user_id: uuid.UUID, refresh_token_str: Optional[str] = None) -> bool:
        """Revoke refresh token(s) upon user sign-out."""
        if refresh_token_str:
            await self.refresh_token_repo.revoke_token(refresh_token_str)
        else:
            await self.refresh_token_repo.revoke_all_for_user(user_id)
        return True

    async def forgot_password(self, email: str) -> str:
        """Generate a secure password reset token for valid accounts."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Return generic confirmation to prevent user enumeration attacks
            return "If an account exists with this email, a reset link has been dispatched."

        reset_token = create_password_reset_token(user.email)
        logger.info(f"Password reset token dispatched for {user.email}: {reset_token[:25]}...")
        return "If an account exists with this email, a reset link has been dispatched."

    async def reset_password(self, token_str: str, new_password: str) -> bool:
        """Validate reset token, update hashed password, and revoke existing sessions."""
        payload = decode_token(token_str)
        if not payload or payload.get("type") != "password_reset":
            raise BadRequestException("Invalid or expired password reset token.")

        email = payload.get("sub")
        if not email:
            raise BadRequestException("Malformed reset token.")

        user = await self.user_repo.get_by_email(email)
        if not user:
            raise EntityNotFoundException("User", email)

        user.hashed_password = get_password_hash(new_password)
        self.session.add(user)

        # Invalidate all active refresh tokens on password change
        await self.refresh_token_repo.revoke_all_for_user(user.id)
        await self.session.flush()
        return True

    async def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """Allow an authenticated user to change their password."""
        if not verify_password(current_password, user.hashed_password):
            raise BadRequestException("Current password does not match our records.")

        user.hashed_password = get_password_hash(new_password)
        self.session.add(user)
        await self.refresh_token_repo.revoke_all_for_user(user.id)
        await self.session.flush()
        return True

    async def verify_email(self, token_str: str) -> bool:
        """Validate email verification token and update verified flag."""
        payload = decode_token(token_str)
        if not payload or payload.get("type") != "email_verification":
            raise BadRequestException("Invalid or expired email verification token.")

        email = payload.get("sub")
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise EntityNotFoundException("User", email)

        user.is_verified = True
        self.session.add(user)
        await self.session.flush()
        return True

    async def resend_verification(self, email: str) -> str:
        """Resend email verification token."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            return "If your account is registered, a new verification link has been sent."

        token = create_email_verification_token(user.email)
        logger.info(f"Re-sent email verification token for {user.email}: {token[:20]}...")
        return "If your account is registered, a new verification link has been sent."

    async def get_current_user_profile(self, user_id: uuid.UUID) -> User:
        """Fetch user with provider profile eagerly loaded."""
        user = await self.user_repo.get_by_id_with_profile(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return user

    async def update_profile(self, user: User, data: ProfileUpdateRequest) -> User:
        """Update customer or provider profile attributes."""
        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if data.phone is not None:
            user.phone = data.phone.strip()
        if data.city is not None:
            user.city = data.city.strip()
        if data.state is not None:
            user.state = data.state.strip()
        if data.zip_code is not None:
            user.zip_code = data.zip_code.strip()
        if data.default_address is not None:
            user.default_address = data.default_address.strip()

        # If user is a provider, update provider-specific fields
        if user.role == UserRole.PROVIDER:
            provider = await self.provider_repo.get_by_user_id(user.id)
            if provider:
                if data.business_name is not None:
                    provider.business_name = data.business_name.strip()
                if data.trade is not None:
                    provider.trade = data.trade.strip()
                if data.bio is not None:
                    provider.bio = data.bio.strip()
                if data.hourly_rate is not None:
                    provider.hourly_rate = data.hourly_rate
                if data.service_radius_miles is not None:
                    provider.service_radius_miles = data.service_radius_miles
                if data.is_available is not None:
                    provider.is_available = data.is_available
                self.session.add(provider)

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_avatar(self, user: User, avatar_url: str) -> User:
        """Update user avatar image URL."""
        user.avatar_url = avatar_url
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
