import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, model_validator

from app.models.store import MerchantType, StoreStatus
from app.models.store_document import DocumentStatus, DocumentType
from app.services.store_hours import is_store_open


class StoreDocumentResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    document_type: DocumentType
    file_url: str
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class PrintServerUrlRequest(BaseModel):
    print_server_url: str = Field(min_length=1, max_length=255)


class StoreUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    phone: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    opening_time: time | None = None
    closing_time: time | None = None
    min_order: float | None = Field(None, ge=0)
    delivery_fee: float | None = Field(None, ge=0)
    # Restaurant-only
    cuisine_type: str | None = None
    average_prep_time: int | None = Field(None, ge=0)
    has_dine_in: bool | None = None
    # Store-only
    store_category: str | None = None
    has_delivery_only: bool | None = None


class StoreImageResponse(BaseModel):
    id: uuid.UUID
    image_url: str
    thumbnail_url: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class StoreResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    merchant_type: MerchantType
    name: str
    description: str | None
    phone: str | None
    address: str
    latitude: float | None
    longitude: float | None
    logo_url: str | None
    cover_image_url: str | None
    status: StoreStatus
    is_open: bool
    opening_time: time | None
    closing_time: time | None
    min_order: float
    delivery_fee: float
    # Restaurant-only
    cuisine_type: str | None
    average_prep_time: int | None
    has_dine_in: bool | None
    # Store-only
    store_category: str | None
    has_delivery_only: bool | None
    print_server_url: str | None
    images: list[StoreImageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_is_open(self) -> "StoreResponse":
        if self.opening_time is not None and self.closing_time is not None:
            self.is_open = is_store_open(self.opening_time, self.closing_time)
        else:
            self.is_open = False
        return self
