import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        result = await self._db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def find_by_phone(self, phone: str) -> User | None:
        result = await self._db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str | None = None,
        phone: str | None = None,
        password_hash: str | None = None,
        full_name: str,
        role: UserRole = UserRole.CUSTOMER,
        phone_verified: bool = False,
    ) -> User:
        user = User(
            email=email,
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            phone_verified=phone_verified,
        )
        self._db.add(user)
        await self._db.flush()
        return user

    async def update_role(self, user: User, role: UserRole) -> User:
        updated = User(
            id=user.id,
            phone=user.phone,
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=role,
            is_active=user.is_active,
            phone_verified=user.phone_verified,
            created_at=user.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def update_active(self, user: User, is_active: bool) -> User:
        updated = User(
            id=user.id,
            phone=user.phone,
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=user.role,
            is_active=is_active,
            phone_verified=user.phone_verified,
            created_at=user.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def update_profile(self, user: User, full_name: str) -> User:
        updated = User(
            id=user.id,
            phone=user.phone,
            email=user.email,
            password_hash=user.password_hash,
            full_name=full_name,
            role=user.role,
            is_active=user.is_active,
            phone_verified=user.phone_verified,
            created_at=user.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def update_email(self, user: User, email: str) -> User:
        updated = User(
            id=user.id,
            phone=user.phone,
            email=email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            phone_verified=user.phone_verified,
            created_at=user.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def update_phone(
        self, user: User, phone: str, phone_verified: bool = True,
    ) -> User:
        updated = User(
            id=user.id,
            phone=phone,
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            phone_verified=phone_verified,
            created_at=user.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def list_users(
        self, *, role: UserRole | None = None, offset: int = 0, limit: int = 20
    ) -> list[User]:
        query = (
            select(User).offset(offset).limit(limit).order_by(User.created_at.desc())
        )
        print(query)
        if role is not None:
            query = query.where(User.role == role)
        result = await self._db.execute(query)
        return list(result.scalars().all())
