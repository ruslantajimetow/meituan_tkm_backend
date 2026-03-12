import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StoreRating(Base):
    __tablename__ = "store_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "store_id", name="uq_store_rating_user_store"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    stars: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProductReview(Base):
    __tablename__ = "product_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "menu_item_id", name="uq_product_review_user_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), index=True)
    stars: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Merchant reply
    merchant_reply: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
