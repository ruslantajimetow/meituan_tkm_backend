import uuid
from datetime import datetime, time

from pydantic import BaseModel

from app.models.store import MerchantType
from app.schemas.store import StoreImageResponse


class PublicStoreListItem(BaseModel):
    id: uuid.UUID
    merchant_type: MerchantType
    name: str
    description: str | None
    address: str
    logo_url: str | None
    cover_image_url: str | None
    is_open: bool
    min_order: float
    delivery_fee: float
    cuisine_type: str | None
    store_category: str | None

    model_config = {"from_attributes": True}


class PublicStoreDetail(PublicStoreListItem):
    phone: str | None
    latitude: float | None
    longitude: float | None
    opening_time: time | None
    closing_time: time | None
    average_prep_time: int | None
    has_dine_in: bool | None
    has_delivery_only: bool | None
    images: list[StoreImageResponse]
    created_at: datetime


class PublicStorePaginatedResponse(BaseModel):
    items: list[PublicStoreListItem]
    total: int
    offset: int
    limit: int
