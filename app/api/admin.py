import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.notification import NotificationType
from app.models.store import StoreStatus
from app.models.user import User, UserRole
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import AdminStoreDetailResponse, StoreStatusUpdateRequest, UserActiveUpdateRequest
from app.schemas.auth import MessageResponse, UserResponse
from app.schemas.store import StoreResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/stores", response_model=list[StoreResponse])
async def list_stores(
    store_status: StoreStatus | None = Query(None, alias="status"),
    search: str | None = None,
    offset: int = 0,
    limit: int = 20,
    _user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    repo = StoreRepository(db)
    return await repo.list_stores(status=store_status, search=search, offset=offset, limit=limit)


@router.get("/stores/{store_id}", response_model=AdminStoreDetailResponse)
async def get_store(
    store_id: uuid.UUID,
    _user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    repo = StoreRepository(db)
    store = await repo.find_by_id_with_details(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )
    return store


@router.patch("/stores/{store_id}/status", response_model=StoreResponse)
async def update_store_status(
    store_id: uuid.UUID,
    body: StoreStatusUpdateRequest,
    _user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    repo = StoreRepository(db)
    store = await repo.find_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )
    updated_store = await repo.update(store, status=body.status)

    # Notify the store owner about status change
    if body.status in (StoreStatus.APPROVED, StoreStatus.REJECTED):
        notifier = NotificationService(db)
        if body.status == StoreStatus.APPROVED:
            n_type = NotificationType.STORE_APPROVED
            title = "Store approved!"
            body_text = (
                f'Your store "{store.name}" has been approved. '
                "You can now add products and start receiving orders."
            )
        else:
            n_type = NotificationType.STORE_REJECTED
            title = "Store not approved"
            body_text = (
                f'Your store "{store.name}" was not approved. '
                "Please contact support for details."
            )

        await notifier.notify(
            user_id=store.owner_id,
            notification_type=n_type,
            title=title,
            body=body_text,
            data={"store_id": str(store.id), "status": body.status.value},
        )

    return updated_store


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    role: UserRole | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 20,
    _user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    return await repo.list_users(role=role, search=search, offset=offset, limit=limit)


@router.patch("/users/{user_id}/active", response_model=MessageResponse)
async def update_user_active(
    user_id: uuid.UUID,
    body: UserActiveUpdateRequest,
    _user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await repo.update_active(user, body.is_active)
    action = "activated" if body.is_active else "deactivated"
    return MessageResponse(message=f"User {action}")
