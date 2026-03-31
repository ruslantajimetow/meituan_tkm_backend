import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.store_document import StoreDocument
from app.models.user import User, UserRole
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(db)
    user = await repo.find_by_id(uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


def require_role(*roles: UserRole) -> Callable:
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker


async def require_merchant_with_documents(
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that ensures the merchant has uploaded at least one document."""
    repo = StoreRepository(db)
    store = await repo.find_by_owner(user.id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    result = await db.execute(
        select(func.count())
        .select_from(StoreDocument)
        .where(StoreDocument.store_id == store.id)
    )
    if result.scalar_one() == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Documents required. Please upload your business documents.",
        )
    return user
