import uuid
from datetime import datetime, time

from pydantic import BaseModel, model_validator

from app.models.store import MerchantType
from app.schemas.store import StoreImageResponse
from app.services.store_hours import is_store_open


class PublicStoreListItem(BaseModel):
    id: uuid.UUID
    merchant_type: MerchantType
    name: str
    description: str | None
    address: str
    logo_url: str | None
    cover_image_url: str | None
    is_open: bool
    opening_time: time | None
    closing_time: time | None
    min_order: float
    delivery_fee: float
    cuisine_type: str | None
    store_category: str | None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_is_open(self) -> "PublicStoreListItem":
        if self.opening_time is not None and self.closing_time is not None:
            self.is_open = is_store_open(self.opening_time, self.closing_time)
        else:
            self.is_open = False
        return self


class PublicStoreDetail(PublicStoreListItem):
    phone: str | None
    latitude: float | None
    longitude: float | None
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


class SearchProductItem(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    store_name: str
    name: str
    description: str | None
    price: float
    image_url: str | None
    thumbnail_url: str | None

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    stores: list[PublicStoreListItem]
    products: list[SearchProductItem]
