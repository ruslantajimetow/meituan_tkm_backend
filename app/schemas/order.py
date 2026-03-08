import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderItemCreateRequest(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1)


class CreateOrderRequest(BaseModel):
    store_id: uuid.UUID
    items: list[OrderItemCreateRequest] = Field(min_length=1)
    delivery_address: str = Field(min_length=1)
    delivery_latitude: float | None = None
    delivery_longitude: float | None = None
    note: str | None = None


class CancelOrderRequest(BaseModel):
    reason: str | None = None


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID | None
    name: str
    quantity: int
    unit_price: float
    total_price: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    store_id: uuid.UUID
    status: OrderStatus
    delivery_address: str
    delivery_latitude: float | None
    delivery_longitude: float | None
    subtotal: float
    delivery_fee: float
    total: float
    note: str | None
    cancelled_reason: str | None
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
