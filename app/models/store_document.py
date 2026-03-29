import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentType(str, enum.Enum):
    BUSINESS_REGISTRATION = "business_registration"
    FOOD_SAFETY_PERMIT = "food_safety_permit"
    TAX_REGISTRATION = "tax_registration"
    STORE_PHOTO = "store_photo"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StoreDocument(Base):
    __tablename__ = "store_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="documenttype"))
    file_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="documentstatus"), default=DocumentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    store: Mapped["Store"] = relationship(back_populates="documents")  # type: ignore[name-defined]
