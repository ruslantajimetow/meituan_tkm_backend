import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.menu_item import MenuItemStatus


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sort_order: int = 0


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MenuItemCreateRequest(BaseModel):
    category_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: float = Field(gt=0)
    sort_order: int = 0
    # Restaurant-only
    portion_size: str | None = None
    is_spicy: bool | None = None
    allergens: list[str] | None = None
    # Store-only
    weight: float | None = Field(None, gt=0)
    unit: str | None = None
    sku: str | None = None


class MenuItemUpdateRequest(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    sort_order: int | None = None
    # Restaurant-only
    portion_size: str | None = None
    is_spicy: bool | None = None
    allergens: list[str] | None = None
    # Store-only
    weight: float | None = Field(None, gt=0)
    unit: str | None = None
    sku: str | None = None


class MenuItemStatusRequest(BaseModel):
    status: MenuItemStatus


class MenuItemResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    category_id: uuid.UUID | None
    name: str
    description: str | None
    price: float
    image_url: str | None
    thumbnail_url: str | None
    status: MenuItemStatus
    sort_order: int
    # Restaurant-only
    portion_size: str | None
    is_spicy: bool | None
    allergens: list[str] | None
    # Store-only
    weight: float | None
    unit: str | None
    sku: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
