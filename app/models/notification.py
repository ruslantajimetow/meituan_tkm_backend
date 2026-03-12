import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationType(str, enum.Enum):
    STORE_REGISTERED = "store_registered"
    STORE_APPROVED = "store_approved"
    STORE_REJECTED = "store_rejected"
    ORDER_NEW = "order_new"
    ORDER_STATUS = "order_status"
    ORDER_CANCELLED = "order_cancelled"
    STORE_RATED = "store_rated"
    PRODUCT_REVIEWED = "product_reviewed"
    NEW_MESSAGE = "new_message"
    REVIEW_REPLY = "review_reply"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True,
    )
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, values_callable=lambda e: [x.value for x in e]))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    data: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
