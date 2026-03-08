import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.menu_item import MenuItem, MenuItemStatus
from app.models.order import OrderStatus
from app.models.store import Store, StoreStatus
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.schemas.order import CancelOrderRequest, CreateOrderRequest, OrderResponse

router = APIRouter()


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    # Validate store
    result = await db.execute(select(Store).where(Store.id == body.store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    if store.status != StoreStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Store is not approved")
    if not store.is_open:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Store is currently closed")

    # Fetch all requested menu items in one query
    requested_ids = [item.menu_item_id for item in body.items]
    result = await db.execute(
        select(MenuItem).where(MenuItem.id.in_(requested_ids), MenuItem.store_id == body.store_id)
    )
    menu_items_by_id = {item.id: item for item in result.scalars().all()}

    # Validate every requested item
    for req_item in body.items:
        menu_item = menu_items_by_id.get(req_item.menu_item_id)
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item {req_item.menu_item_id} not found in this store",
            )
        if menu_item.status != MenuItemStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' is not available",
            )

    # Compute totals with snapshotted prices
    order_items = []
    subtotal = Decimal("0")
    for req_item in body.items:
        menu_item = menu_items_by_id[req_item.menu_item_id]
        unit_price = Decimal(str(menu_item.price))
        item_total = unit_price * req_item.quantity
        subtotal += item_total
        order_items.append({
            "menu_item_id": menu_item.id,
            "name": menu_item.name,
            "quantity": req_item.quantity,
            "unit_price": float(unit_price),
            "total_price": float(item_total),
        })

    if subtotal < Decimal(str(store.min_order)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum order amount is {store.min_order}",
        )

    delivery_fee = Decimal(str(store.delivery_fee))
    total = subtotal + delivery_fee

    repo = OrderRepository(db)
    order = await repo.create(
        customer_id=user.id,
        store_id=store.id,
        delivery_address=body.delivery_address,
        delivery_latitude=body.delivery_latitude,
        delivery_longitude=body.delivery_longitude,
        subtotal=float(subtotal),
        delivery_fee=float(delivery_fee),
        total=float(total),
        note=body.note,
        items=order_items,
    )
    return order


@router.get("", response_model=list[OrderResponse])
async def list_my_orders(
    order_status: OrderStatus | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    return await repo.list_by_customer(user.id, status=order_status, offset=offset, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_my_order(
    order_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_customer(order_id, user.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    body: CancelOrderRequest,
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_customer(order_id, user.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be cancelled",
        )
    return await repo.update_status(order, OrderStatus.CANCELLED, cancelled_reason=body.reason)
