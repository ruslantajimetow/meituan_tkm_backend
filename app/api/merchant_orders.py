import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import Errors
from app.middleware.auth import require_merchant_with_documents
from app.models.notification import NotificationType
from app.models.order import OrderStatus
from app.models.store import MerchantType
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.order import OrderResponse, UpdateOrderStatusRequest
from app.services.notification_service import NotificationService
from app.services.print_service import print_order_receipt

router = APIRouter()

RESTAURANT_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.RECEIVED, OrderStatus.CANCELLED},
    OrderStatus.RECEIVED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.SENT},
    OrderStatus.SENT: {OrderStatus.DELIVERED},
}

STORE_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.RECEIVED, OrderStatus.CANCELLED},
    OrderStatus.RECEIVED: {OrderStatus.SENT, OrderStatus.CANCELLED},
    OrderStatus.SENT: {OrderStatus.DELIVERED},
}


def _get_transitions(merchant_type: MerchantType) -> dict[OrderStatus, set[OrderStatus]]:
    if merchant_type == MerchantType.RESTAURANT:
        return RESTAURANT_TRANSITIONS
    return STORE_TRANSITIONS


async def _get_merchant_store(user: User, db: AsyncSession):
    repo = StoreRepository(db)
    store = await repo.find_by_owner(user.id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Errors.store_not_found())
    return store


@router.get("", response_model=list[OrderResponse])
async def list_store_orders(
    order_status: OrderStatus | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(require_merchant_with_documents),
    db: AsyncSession = Depends(get_db),
):
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    orders = await repo.list_by_store(
        store.id, status=order_status, search=search, offset=offset, limit=limit,
    )
    return [OrderResponse.from_order(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_store_order(
    order_id: uuid.UUID,
    user: User = Depends(require_merchant_with_documents),
    db: AsyncSession = Depends(get_db),
):
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_store(order_id, store.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Errors.order_not_found())
    return OrderResponse.from_order(order)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    body: UpdateOrderStatusRequest,
    user: User = Depends(require_merchant_with_documents),
    db: AsyncSession = Depends(get_db),
):
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_store(order_id, store.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Errors.order_not_found())

    transitions = _get_transitions(store.merchant_type)
    allowed = transitions.get(order.status, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.invalid_order_transition(order.status.value, body.status.value),
        )

    updated = await repo.update_status(order, body.status)

    # Notify customer of status change
    notifier = NotificationService(db)
    status_label = body.status.value.replace("_", " ").title()
    await notifier.notify(
        user_id=order.customer_id,
        notification_type=NotificationType.ORDER_STATUS,
        title="Order Update",
        body=f"Your order is now {status_label}",
        data={"order_id": str(order.id), "status": body.status.value},
    )

    return OrderResponse.from_order(updated)


@router.post("/{order_id}/print", response_model=dict)
async def reprint_order_receipt(
    order_id: uuid.UUID,
    user: User = Depends(require_merchant_with_documents),
    db: AsyncSession = Depends(get_db),
):
    """Reprint a receipt for an order. Auto-receives the order if still PENDING."""
    store = await _get_merchant_store(user, db)
    repo = OrderRepository(db)
    order = await repo.find_by_id_and_store(order_id, store.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Errors.order_not_found())
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.order_already_cancelled(),
        )

    printed = await print_order_receipt(order, store.print_server_url)

    # Auto-receive if still pending and print succeeded
    if printed and order.status == OrderStatus.PENDING:
        await repo.update_status(order, OrderStatus.RECEIVED)

    return {"printed": printed}
