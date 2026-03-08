from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp_code import OtpCode


class OtpRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, *, phone: str, code: str, expires_at: datetime) -> OtpCode:
        otp = OtpCode(phone=phone, code=code, expires_at=expires_at)
        self._db.add(otp)
        await self._db.flush()
        return otp

    async def find_valid(self, phone: str, code: str) -> OtpCode | None:
        now = datetime.now(UTC)
        result = await self._db.execute(
            select(OtpCode)
            .where(
                OtpCode.phone == phone,
                OtpCode.code == code,
                OtpCode.used == False,  # noqa: E712
                OtpCode.expires_at > now,
            )
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def increment_attempts(self, otp: OtpCode) -> OtpCode:
        updated = OtpCode(
            id=otp.id,
            phone=otp.phone,
            code=otp.code,
            expires_at=otp.expires_at,
            used=otp.used,
            attempts=otp.attempts + 1,
            created_at=otp.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def mark_used(self, otp: OtpCode) -> OtpCode:
        updated = OtpCode(
            id=otp.id,
            phone=otp.phone,
            code=otp.code,
            expires_at=otp.expires_at,
            used=True,
            attempts=otp.attempts,
            created_at=otp.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def count_recent_sends(self, phone: str, since: datetime) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.created_at >= since)
        )
        return result.scalar_one()
