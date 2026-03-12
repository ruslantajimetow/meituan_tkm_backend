import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            data=data,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .offset(offset)
            .limit(limit)
            .order_by(Notification.created_at.desc())
        )
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        await self._db.flush()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self._db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self._db.flush()
        return result.rowcount

    async def mark_read_by_types(
        self,
        user_id: uuid.UUID,
        types: list[NotificationType],
    ) -> int:
        result = await self._db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.type.in_(types),
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self._db.flush()
        return result.rowcount

    async def mark_read_by_store(
        self,
        user_id: uuid.UUID,
        store_id: uuid.UUID,
    ) -> int:
        result = await self._db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.type == NotificationType.STORE_REGISTERED,
                Notification.is_read.is_(False),
                Notification.data.contains(str(store_id)),
            )
            .values(is_read=True)
        )
        await self._db.flush()
        return result.rowcount
