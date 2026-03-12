import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.auth import MessageResponse
from app.models.notification import NotificationType
from app.schemas.notification import (
    MarkReadByStoreRequest,
    MarkReadByTypesRequest,
    NotificationResponse,
    UnreadCountResponse,
)

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    return await repo.list_by_user(user.id, unread_only=unread_only, offset=offset, limit=limit)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    items = await repo.list_by_user(user.id, unread_only=True, limit=100)
    return UnreadCountResponse(count=len(items))


@router.patch("/{notification_id}/read", response_model=MessageResponse)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    updated = await repo.mark_read(notification_id, user.id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return MessageResponse(message="Marked as read")


@router.patch("/read-all", response_model=MessageResponse)
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    count = await repo.mark_all_read(user.id)
    return MessageResponse(message=f"Marked {count} notifications as read")


@router.patch("/read-by-types", response_model=MessageResponse)
async def mark_read_by_types(
    body: MarkReadByTypesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    valid_types = []
    for t in body.types:
        try:
            valid_types.append(NotificationType(t))
        except ValueError:
            continue
    if not valid_types:
        return MessageResponse(message="No valid types provided")
    count = await repo.mark_read_by_types(user.id, valid_types)
    return MessageResponse(message=f"Marked {count} notifications as read")


@router.patch("/read-by-store", response_model=MessageResponse)
async def mark_read_by_store(
    body: MarkReadByStoreRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NotificationRepository(db)
    count = await repo.mark_read_by_store(user.id, body.store_id)
    return MessageResponse(message=f"Marked {count} notifications as read")
