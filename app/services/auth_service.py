import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self._user_repo = UserRepository(db)
        self._token_repo = TokenRepository(db)

    async def register_merchant_with_email(
        self, *, email: str, password: str, full_name: str
    ) -> tuple[TokenResponse, uuid.UUID]:
        existing = await self._user_repo.find_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = await self._user_repo.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.MERCHANT,
        )
        tokens = await self._issue_tokens(user.id, user.role)
        return tokens, user.id

    async def register_with_email(
        self, *, email: str, password: str, full_name: str
    ) -> TokenResponse:
        existing = await self._user_repo.find_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = await self._user_repo.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )
        return await self._issue_tokens(user.id, user.role)

    async def login_with_email(self, *, email: str, password: str) -> TokenResponse:
        user = await self._user_repo.find_by_email(email)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        return await self._issue_tokens(user.id, user.role)

    async def login_with_phone(self, user: User) -> TokenResponse:
        """Issue tokens for an existing phone-verified user."""
        return await self._issue_tokens(user.id, user.role)

    async def complete_registration(
        self,
        *,
        phone: str,
        full_name: str,
        role: UserRole,
    ) -> tuple[TokenResponse, uuid.UUID]:
        existing = await self._user_repo.find_by_phone(phone)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone already registered",
            )

        user = await self._user_repo.create(
            phone=phone,
            full_name=full_name,
            role=role,
            phone_verified=True,
        )
        tokens = await self._issue_tokens(user.id, user.role)
        return tokens, user.id

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        stored = await self._token_repo.find_by_hash(token_hash)
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        now = datetime.now(UTC)
        if stored.expires_at < now:
            await self._token_repo.revoke(stored)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        # Rotate: revoke old, issue new
        await self._token_repo.revoke(stored)

        user = await self._user_repo.find_by_id(stored.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )
        return await self._issue_tokens(user.id, user.role)

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        stored = await self._token_repo.find_by_hash(token_hash)
        if stored:
            await self._token_repo.revoke(stored)

    async def _issue_tokens(self, user_id: uuid.UUID, role: UserRole) -> TokenResponse:
        access_token = create_access_token({"sub": str(user_id), "role": role.value})
        refresh_token = create_refresh_token()

        expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
        await self._token_repo.create(
            user_id=user_id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
