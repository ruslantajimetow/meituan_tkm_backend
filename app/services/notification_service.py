import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationType
from app.repositories.notification_repository import NotificationRepository
from app.services.ws_manager import ws_manager


class NotificationService:
    def __init__(self, db: AsyncSession):
        self._repo = NotificationRepository(db)

    async def notify(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        data_str = json.dumps(data, default=str) if data else None

        notification = await self._repo.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data_str,
        )

        await ws_manager.send_to_user(user_id, {
            "type": "notification",
            "payload": {
                "id": str(notification.id),
                "notification_type": notification_type.value,
                "title": title,
                "body": body,
                "data": data,
                "is_read": False,
                "created_at": notification.created_at.isoformat(),
            },
        })

    async def notify_many(
        self,
        *,
        user_ids: list[uuid.UUID],
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        for user_id in user_ids:
            await self.notify(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data,
            )
