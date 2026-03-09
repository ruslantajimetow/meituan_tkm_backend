from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import MessageResponse, UserResponse
from app.schemas.profile import (
    BindPhoneVerifyRequest,
    UpdateEmailRequest,
    UpdatePhoneRequest,
)
from app.services.otp_service import OtpService
from app.services.sms_provider import get_otp_provider

router = APIRouter()


@router.put("/email", response_model=UserResponse)
async def update_email(
    body: UpdateEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    existing = await repo.find_by_email(body.email)
    if existing and existing.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already in use by another account",
        )
    updated = await repo.update_email(user, body.email)
    return updated


@router.post("/phone/send-otp", response_model=MessageResponse)
async def send_phone_otp(
    body: UpdatePhoneRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    existing = await repo.find_by_phone(body.phone)
    if existing and existing.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number is already in use by another account",
        )
    otp_service = OtpService(db, get_otp_provider())
    await otp_service.send_otp(body.phone)
    return MessageResponse(message="OTP sent successfully")


@router.post("/phone/verify", response_model=UserResponse)
async def verify_and_bind_phone(
    body: BindPhoneVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    existing = await repo.find_by_phone(body.phone)
    if existing and existing.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number is already in use by another account",
        )
    otp_service = OtpService(db, get_otp_provider())
    await otp_service.verify_otp(body.phone, body.code)
    updated = await repo.update_phone(user, body.phone)
    return updated
