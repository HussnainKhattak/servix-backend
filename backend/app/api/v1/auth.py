import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BadRequestException
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.base import ApiResponse
from app.schemas.auth import (
    LoginRequest,
    RegisterCustomerRequest,
    RegisterProviderRequest,
    RefreshTokenRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ProfileUpdateRequest,
    TokenResponse,
    CurrentUserResponse,
)
from app.services.auth_service import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


@router.post(
    "/register/customer",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Customer",
)
async def register_customer(
    data: RegisterCustomerRequest,
    session: AsyncSession = Depends(get_db),
):
    """Register a new customer account and return authentication tokens."""
    service = AuthService(session)
    user, tokens = await service.register_customer(data)
    return success_response(
        data=tokens,
        message=f"Customer account created successfully for {user.email}.",
    )


@router.post(
    "/register/provider",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Service Provider",
)
async def register_provider(
    data: RegisterProviderRequest,
    session: AsyncSession = Depends(get_db),
):
    """Register a new trade service provider account and return authentication tokens."""
    service = AuthService(session)
    user, tokens = await service.register_provider(data)
    return success_response(
        data=tokens,
        message=f"Provider account created successfully for {user.email}.",
    )


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="User Login",
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password to receive JWT access and refresh tokens."""
    service = AuthService(session)
    tokens = await service.authenticate(data)
    return success_response(
        data=tokens,
        message="Logged in successfully.",
    )


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Refresh Access Token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """Submit a valid refresh token to obtain a fresh access token (with token rotation)."""
    service = AuthService(session)
    tokens = await service.refresh_tokens(data.refresh_token)
    return success_response(
        data=tokens,
        message="Token refreshed successfully.",
    )


@router.post(
    "/logout",
    response_model=ApiResponse[bool],
    summary="User Logout",
)
async def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Revoke refresh token and invalidate the active session."""
    service = AuthService(session)
    await service.logout(current_user.id, data.refresh_token)
    return success_response(
        data=True,
        message="Logged out successfully.",
    )


@router.post(
    "/forgot-password",
    response_model=ApiResponse[str],
    summary="Forgot Password",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """Dispatch a secure password reset link to the registered email address."""
    service = AuthService(session)
    msg = await service.forgot_password(data.email)
    return success_response(data=msg, message=msg)


@router.post(
    "/reset-password",
    response_model=ApiResponse[bool],
    summary="Reset Password",
)
async def reset_password(
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """Set a new password using a verified password reset token."""
    service = AuthService(session)
    await service.reset_password(data.token, data.new_password)
    return success_response(
        data=True,
        message="Password has been reset successfully. Please log in with your new password.",
    )


@router.post(
    "/change-password",
    response_model=ApiResponse[bool],
    summary="Change Password",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Change the current user's password (requires current password)."""
    service = AuthService(session)
    await service.change_password(current_user, data.current_password, data.new_password)
    return success_response(
        data=True,
        message="Password updated successfully.",
    )


@router.post(
    "/verify-email",
    response_model=ApiResponse[bool],
    summary="Verify Email Address",
)
async def verify_email(
    data: VerifyEmailRequest,
    session: AsyncSession = Depends(get_db),
):
    """Verify an email address using the received verification token."""
    service = AuthService(session)
    await service.verify_email(data.token)
    return success_response(
        data=True,
        message="Email address verified successfully.",
    )


@router.post(
    "/resend-verification",
    response_model=ApiResponse[str],
    summary="Resend Verification Email",
)
async def resend_verification(
    data: ResendVerificationRequest,
    session: AsyncSession = Depends(get_db),
):
    """Resend email verification link."""
    service = AuthService(session)
    msg = await service.resend_verification(data.email)
    return success_response(data=msg, message=msg)


@router.get(
    "/me",
    response_model=ApiResponse[CurrentUserResponse],
    summary="Get Current Authenticated User",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetch the currently authenticated user's complete profile, roles, and provider profile."""
    service = AuthService(session)
    user_with_profile = await service.get_current_user_profile(current_user.id)
    return success_response(
        data=CurrentUserResponse.model_validate(user_with_profile),
        message="Profile retrieved successfully.",
    )


@router.put(
    "/profile",
    response_model=ApiResponse[CurrentUserResponse],
    summary="Update Profile",
)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update profile information (contact info, address, and provider trade details)."""
    service = AuthService(session)
    updated_user = await service.update_profile(current_user, data)
    user_with_profile = await service.get_current_user_profile(updated_user.id)
    return success_response(
        data=CurrentUserResponse.model_validate(user_with_profile),
        message="Profile updated successfully.",
    )


@router.post(
    "/avatar",
    response_model=ApiResponse[CurrentUserResponse],
    summary="Upload Profile Avatar Image",
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Upload a profile picture (JPEG, PNG, WebP; max 5MB)."""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise BadRequestException("Invalid file type. Only JPEG, PNG, and WebP images are allowed.")

    # Max 5MB
    max_size = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise BadRequestException("File size exceeds maximum allowed limit (5MB).")

    # Save to local uploads directory
    uploads_dir = os.path.join(os.getcwd(), "uploads", "avatars")
    os.makedirs(uploads_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(uploads_dir, filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    avatar_url = f"/uploads/avatars/{filename}"
    service = AuthService(session)
    await service.update_avatar(current_user, avatar_url)
    user_with_profile = await service.get_current_user_profile(current_user.id)

    return success_response(
        data=CurrentUserResponse.model_validate(user_with_profile),
        message="Profile image uploaded successfully.",
    )
