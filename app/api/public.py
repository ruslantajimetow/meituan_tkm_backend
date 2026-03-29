import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.menu_item import MenuItemStatus
from app.models.store import MerchantType
from app.repositories.menu_repository import MenuRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.menu import CategoryResponse, MenuItemResponse
from app.schemas.public import (
    NearbyStorePaginatedResponse,
    NearbyStoreListItem,
    PublicStoreDetail,
    PublicStorePaginatedResponse,
    SearchProductItem,
    SearchResponse,
)

router = APIRouter()

MAX_LIMIT = 50


@router.get("/categories", response_model=list[str])
async def list_categories(
    merchant_type: MerchantType,
    db: AsyncSession = Depends(get_db),
):
    """Return distinct category values for approved stores of the given merchant type."""
    return await StoreRepository(db).list_distinct_categories(merchant_type)


@router.get("/stores", response_model=PublicStorePaginatedResponse)
async def list_stores(
    merchant_type: MerchantType | None = None,
    search: str | None = None,
    cuisine_type: str | None = None,
    store_category: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
):
    repo = StoreRepository(db)
    stores, total = await repo.list_public(
        merchant_type=merchant_type,
        search=search,
        cuisine_type=cuisine_type,
        store_category=store_category,
        offset=offset,
        limit=limit,
    ), await repo.count_public(
        merchant_type=merchant_type,
        search=search,
        cuisine_type=cuisine_type,
        store_category=store_category,
    )
    return PublicStorePaginatedResponse(items=stores, total=total, offset=offset, limit=limit)


@router.get("/stores/nearby", response_model=NearbyStorePaginatedResponse)
async def list_nearby_stores(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50.0, ge=1, le=200),
    merchant_type: MerchantType | None = None,
    search: str | None = None,
    cuisine_type: str | None = None,
    store_category: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
):
    repo = StoreRepository(db)
    rows = await repo.list_nearby(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        merchant_type=merchant_type,
        search=search,
        cuisine_type=cuisine_type,
        store_category=store_category,
        offset=offset,
        limit=limit,
    )
    total = await repo.count_nearby(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        merchant_type=merchant_type,
        search=search,
        cuisine_type=cuisine_type,
        store_category=store_category,
    )
    items = [
        NearbyStoreListItem.model_validate({**store.__dict__, "distance_km": distance_km})
        for store, distance_km in rows
    ]
    return NearbyStorePaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query("", min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    store_repo = StoreRepository(db)
    menu_repo = MenuRepository(db)

    stores = await store_repo.list_public(search=q, limit=10)
    product_rows = await menu_repo.search_public_products(q, limit=20)

    products = [
        SearchProductItem(
            id=item.id,
            store_id=item.store_id,
            store_name=store_name,
            name=item.name,
            description=item.description,
            price=float(item.price),
            image_url=item.image_url,
            thumbnail_url=item.thumbnail_url,
        )
        for item, store_name in product_rows
    ]

    return SearchResponse(stores=stores, products=products)


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
