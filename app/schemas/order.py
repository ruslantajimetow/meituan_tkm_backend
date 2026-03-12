import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, SpiceLevel


class OrderItemCreateRequest(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1)
    spice_level: SpiceLevel | None = None


class CreateOrderRequest(BaseModel):
    store_id: uuid.UUID
    items: list[OrderItemCreateRequest] = Field(min_length=1)
    customer_phone: str = Field(min_length=1)
    delivery_address: str = Field(min_length=1)
    delivery_latitude: float | None = None
    delivery_longitude: float | None = None
    note: str | None = None


class CancelOrderRequest(BaseModel):
    reason: str = Field(min_length=1)


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID | None
    name: str
    quantity: int
    unit_price: float
    total_price: float
    spice_level: SpiceLevel | None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    store_id: uuid.UUID
    store_name: str = ""
    merchant_type: str = ""
    status: OrderStatus
    customer_phone: str
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

    @classmethod
    def from_order(cls, order) -> "OrderResponse":
        store = getattr(order, "store", None)
        data = {
            "id": order.id,
            "customer_id": order.customer_id,
            "store_id": order.store_id,
            "store_name": store.name if store else "",
            "merchant_type": store.merchant_type.value if store else "",
            "status": order.status,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "delivery_latitude": order.delivery_latitude,
            "delivery_longitude": order.delivery_longitude,
            "subtotal": order.subtotal,
            "delivery_fee": order.delivery_fee,
            "total": order.total,
            "note": order.note,
            "cancelled_reason": order.cancelled_reason,
            "items": order.items,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }
        return cls.model_validate(data, from_attributes=True)
