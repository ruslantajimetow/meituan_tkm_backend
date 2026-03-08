import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.menu_item import MenuItemStatus
from app.models.store import MerchantType
from app.repositories.menu_repository import MenuRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.menu import CategoryResponse, MenuItemResponse
from app.schemas.public import PublicStoreDetail, PublicStorePaginatedResponse

router = APIRouter()

MAX_LIMIT = 50


@router.get("/stores", response_model=PublicStorePaginatedResponse)
async def list_stores(
    merchant_type: MerchantType | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
):
    repo = StoreRepository(db)
    stores, total = await repo.list_public(
        merchant_type=merchant_type, search=search, offset=offset, limit=limit,
    ), await repo.count_public(
        merchant_type=merchant_type, search=search,
    )
    return PublicStorePaginatedResponse(items=stores, total=total, offset=offset, limit=limit)


@router.get("/stores/{store_id}", response_model=PublicStoreDetail)
async def get_store(store_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = StoreRepository(db)
    store = await repo.find_public(store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.get("/stores/{store_id}/categories", response_model=list[CategoryResponse])
async def list_categories(store_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    store_repo = StoreRepository(db)
    store = await store_repo.find_public(store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    menu_repo = MenuRepository(db)
    return await menu_repo.list_categories(store.id)


@router.get("/stores/{store_id}/items", response_model=list[MenuItemResponse])
async def list_items(
    store_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
):
    store_repo = StoreRepository(db)
    store = await store_repo.find_public(store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    menu_repo = MenuRepository(db)
    return await menu_repo.list_items(
        store.id,
        category_id=category_id,
        status=MenuItemStatus.ACTIVE,
        offset=offset,
        limit=limit,
    )
