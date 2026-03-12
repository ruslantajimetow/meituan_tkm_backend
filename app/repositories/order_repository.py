import uuid

from sqlalchemy import cast, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _find(self, *filters) -> Order | None:
        result = await self._db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.store))
            .where(*filters)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, order_id: uuid.UUID) -> Order | None:
        return await self._find(Order.id == order_id)

    async def find_by_id_and_customer(self, order_id: uuid.UUID, customer_id: uuid.UUID) -> Order | None:
        return await self._find(Order.id == order_id, Order.customer_id == customer_id)

    async def find_by_id_and_store(self, order_id: uuid.UUID, store_id: uuid.UUID) -> Order | None:
        return await self._find(Order.id == order_id, Order.store_id == store_id)

    async def _list(
        self,
        *filters,
        status: OrderStatus | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        query = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.store))
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        if status is not None:
            query = query.where(Order.status == status)
        if search:
            query = query.where(cast(Order.id, String).ilike(f"%{search}%"))
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def list_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        status: OrderStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        return await self._list(
            Order.customer_id == customer_id,
            status=status, offset=offset, limit=limit,
        )

    async def list_by_store(
        self,
        store_id: uuid.UUID,
        *,
        status: OrderStatus | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        return await self._list(
            Order.store_id == store_id,
            status=status, search=search, offset=offset, limit=limit,
        )

    async def create(
        self,
        *,
        customer_id: uuid.UUID,
        store_id: uuid.UUID,
        customer_phone: str,
        delivery_address: str,
        delivery_latitude: float | None,
        delivery_longitude: float | None,
        subtotal: float,
        delivery_fee: float,
        total: float,
        note: str | None,
        items: list[dict],
    ) -> Order:
        order = Order(
            customer_id=customer_id,
            store_id=store_id,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            note=note,
        )
        self._db.add(order)
        await self._db.flush()

        for item_data in items:
            order_item = OrderItem(order_id=order.id, **item_data)
            self._db.add(order_item)

        await self._db.flush()
        return await self.find_by_id(order.id)

    async def update_status(
        self,
        order: Order,
        status: OrderStatus,
        cancelled_reason: str | None = None,
    ) -> Order:
        merged_attrs = {
            "id": order.id,
            "customer_id": order.customer_id,
            "store_id": order.store_id,
            "status": status,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "delivery_latitude": order.delivery_latitude,
            "delivery_longitude": order.delivery_longitude,
            "subtotal": order.subtotal,
            "delivery_fee": order.delivery_fee,
            "total": order.total,
            "note": order.note,
            "cancelled_reason": cancelled_reason or order.cancelled_reason,
            "created_at": order.created_at,
        }
        updated = Order(**merged_attrs)
        await self._db.merge(updated)
        await self._db.flush()
        return await self.find_by_id(order.id)
