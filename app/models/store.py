import enum
import uuid
from datetime import UTC, datetime, time

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MerchantType(str, enum.Enum):
    RESTAURANT = "restaurant"
    STORE = "store"


class StoreStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    merchant_type: Mapped[MerchantType] = mapped_column(Enum(MerchantType))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[StoreStatus] = mapped_column(Enum(StoreStatus), default=StoreStatus.PENDING)
    is_open: Mapped[bool] = mapped_column(Boolean, default=False)
    opening_time: Mapped[time | None] = mapped_column(Time)
    closing_time: Mapped[time | None] = mapped_column(Time)
    min_order: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    # Restaurant-only fields
    cuisine_type: Mapped[str | None] = mapped_column(String(100))
    average_prep_time: Mapped[int | None] = mapped_column()
    has_dine_in: Mapped[bool | None] = mapped_column(Boolean)

    # Store-only fields
    store_category: Mapped[str | None] = mapped_column(String(100))
    has_delivery_only: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    images: Mapped[list["StoreImage"]] = relationship(back_populates="store", cascade="all, delete-orphan", order_by="StoreImage.sort_order")
    documents: Mapped[list["StoreDocument"]] = relationship(back_populates="store", cascade="all, delete-orphan", order_by="StoreDocument.created_at")  # type: ignore[name-defined]


class StoreImage(Base):
    __tablename__ = "store_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    image_url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    store: Mapped["Store"] = relationship(back_populates="images")
