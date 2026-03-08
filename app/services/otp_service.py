from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.otp_repository import OtpRepository
from app.services.sms_provider import OtpProvider


class OtpService:
    def __init__(self, db: AsyncSession, otp_provider: OtpProvider):
        self._otp_repo = OtpRepository(db)
        self._otp_provider = otp_provider

    async def send_otp(self, phone: str) -> None:
        # Rate limit check (local, applies to all providers)
        since = datetime.now(UTC) - timedelta(minutes=settings.otp_rate_limit_minutes)
        recent_count = await self._otp_repo.count_recent_sends(phone, since)
        if recent_count >= settings.otp_max_sends_per_phone:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many OTP requests. Try again in {settings.otp_rate_limit_minutes} minutes.",
            )

        sent = await self._otp_provider.send_otp(phone)
        if not sent:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to send OTP. Please try again.",
            )

        # Track the send for rate limiting
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.otp_expire_minutes)
        await self._otp_repo.create(phone=phone, code="provider-managed", expires_at=expires_at)

    async def verify_otp(self, phone: str, code: str) -> bool:
        """Verify OTP via the provider. Returns True if valid."""
        valid = await self._otp_provider.verify_otp(phone, code)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP",
            )
        return True
