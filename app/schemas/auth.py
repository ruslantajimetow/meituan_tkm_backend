import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OtpSendRequest(BaseModel):
    phone: str = Field(pattern=r"^\+993\d{8}$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return v.strip()


class OtpVerifyRequest(BaseModel):
    phone: str = Field(pattern=r"^\+993\d{8}$")
    code: str = Field(min_length=6, max_length=6)


class RegisterCompleteRequest(BaseModel):
    registration_token: str
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.CUSTOMER
    # Merchant fields (required when role=merchant)
    store_name: str | None = Field(None, min_length=1, max_length=255)
    merchant_type: str | None = Field(None, pattern=r"^(restaurant|store)$")
    address: str | None = None
    # Store location (optional but strongly recommended)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    store_phone: str | None = None
    description: str | None = None
    # Restaurant-only
    cuisine_type: str | None = None
    average_prep_time: int | None = None
    has_dine_in: bool | None = None
    # Store-only
    store_category: str | None = None
    has_delivery_only: bool | None = None

    @field_validator("store_name", "merchant_type", "address")
    @classmethod
    def merchant_fields_required(cls, v, info):
        # These are validated at the route level based on role
        return v


class MerchantEmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    # Store fields (required)
    store_name: str = Field(min_length=1, max_length=255)
    merchant_type: str = Field(pattern=r"^(restaurant|store)$")
    address: str = Field(min_length=1)
    # Store location (optional but strongly recommended)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    # Store fields (optional)
    store_phone: str | None = None
    description: str | None = None
    # Restaurant-only
    cuisine_type: str | None = None
    average_prep_time: int | None = None
    has_dine_in: bool | None = None
    # Store-only
    store_category: str | None = None
    has_delivery_only: bool | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str
    role: UserRole
    is_active: bool
    phone_verified: bool
    has_documents: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
