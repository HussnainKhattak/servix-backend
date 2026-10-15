import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.enums import UserRole
from app.schemas.provider import ProviderResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="User password")
    # role is intentionally omitted — the backend reads it from the DB record


class RegisterCustomerRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password minimum 8 characters")
    full_name: str = Field(min_length=2, max_length=100)
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    default_address: Optional[str] = None


class RegisterProviderRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password minimum 8 characters")
    full_name: str = Field(min_length=2, max_length=100)
    phone: str
    business_name: str = Field(min_length=2, max_length=150)
    trade: str = Field(min_length=2, max_length=100)
    license_number: Optional[str] = None
    city: str
    state: str
    zip_code: str
    hourly_rate: Optional[float] = None
    service_radius_miles: float = 15.0


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, description="New password minimum 8 characters")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, description="New password minimum 8 characters")


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    default_address: Optional[str] = None
    # If provider
    business_name: Optional[str] = None
    trade: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    service_radius_miles: Optional[float] = None
    is_available: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: UserRole


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    default_address: Optional[str] = None
    provider_profile: Optional[ProviderResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int
    iat: int
    type: str
