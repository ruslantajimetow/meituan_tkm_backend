import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.middleware.auth import get_current_user
from app.models.store import MerchantType
from app.models.user import User, UserRole
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    OtpSendRequest,
    OtpVerifyRequest,
    RefreshTokenRequest,
    RegisterCompleteRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.otp_service import OtpService
from app.services.sms_provider import get_otp_provider

router = APIRouter()

REGISTRATION_TOKEN_PREFIX = "reg_token:"
REGISTRATION_TOKEN_TTL = 600  # 10 minutes


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.register_with_email(
        email=body.email, password=body.password, full_name=body.full_name
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login_with_email(email=body.email, password=body.password)


@router.post("/otp/send", response_model=MessageResponse)
async def send_otp(body: OtpSendRequest, db: AsyncSession = Depends(get_db)):
    otp_provider = get_otp_provider()
    service = OtpService(db, otp_provider)
    await service.send_otp(body.phone)
    return MessageResponse(message="OTP sent successfully")


@router.post("/otp/verify")
async def verify_otp(
    body: OtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # Verify OTP via provider (UniMTX or mock)
    otp_provider = get_otp_provider()
    otp_service = OtpService(db, otp_provider)
    await otp_service.verify_otp(body.phone, body.code)

    # Check if user exists
    user_repo = UserRepository(db)
    user = await user_repo.find_by_phone(body.phone)

    if user:
        # Existing user — return tokens directly
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        auth_service = AuthService(db)
        return await auth_service.login_with_phone(user)

    # New user — issue a temporary registration token
    reg_token = secrets.token_urlsafe(32)
    await redis.set(
        f"{REGISTRATION_TOKEN_PREFIX}{reg_token}",
        body.phone,
        ex=REGISTRATION_TOKEN_TTL,
    )
    return {
        "registration_token": reg_token,
        "message": "OTP verified. Complete registration at /api/auth/register/complete",
    }


@router.post("/register/complete", response_model=TokenResponse)
async def register_complete(
    body: RegisterCompleteRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # Retrieve phone from registration token
    phone = await redis.getdel(f"{REGISTRATION_TOKEN_PREFIX}{body.registration_token}")
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration token. Verify OTP again.",
        )

    auth_service = AuthService(db)

    if body.role == UserRole.MERCHANT:
        if not body.store_name or not body.merchant_type or not body.address:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="store_name, merchant_type, and address are required for merchants",
            )
        tokens, user_id = await auth_service.complete_registration(
            phone=phone,
            full_name=body.full_name,
            role=UserRole.MERCHANT,
        )
        store_repo = StoreRepository(db)
        await store_repo.create(
            owner_id=user_id,
            merchant_type=MerchantType(body.merchant_type),
            name=body.store_name,
            address=body.address,
            phone=body.store_phone,
            description=body.description,
            cuisine_type=body.cuisine_type,
            average_prep_time=body.average_prep_time,
            has_dine_in=body.has_dine_in,
            store_category=body.store_category,
            has_delivery_only=body.has_delivery_only,
        )
        return tokens

    tokens, _ = await auth_service.complete_registration(
        phone=phone,
        full_name=body.full_name,
        role=body.role,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh_tokens(body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.logout(body.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
