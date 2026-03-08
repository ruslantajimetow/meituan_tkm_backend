import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.order import OrderResponse, UpdateOrderStatusRequest

router = APIRouter()

VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.PICKED_UP},
    OrderStatus.PICKED_UP: {OrderStatus.DELIVERED},
}


async def _get_merchant_store(user: User, db: AsyncSession):
    repo = StoreRepository(db)
    store = await repo.find_by_owner(user.id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.get("", response_model=list[OrderResponse])
async def list_store_orders(
    order_status: OrderStatus | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    return await repo.list_by_store(store.id, status=order_status, offset=offset, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_store_order(
    order_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_store(order_id, store.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    body: UpdateOrderStatusRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_store(order_id, store.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{order.status.value}' to '{body.status.value}'",
        )

    return await repo.update_status(order, body.status)
