import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import delete_image, upload_image, validate_image
from app.middleware.auth import require_role
from app.models.menu_item import MenuItemStatus
from app.models.user import User, UserRole
from app.repositories.menu_repository import MenuRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.auth import MessageResponse
from app.schemas.menu import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    MenuItemCreateRequest,
    MenuItemResponse,
    MenuItemStatusRequest,
    MenuItemUpdateRequest,
)

router = APIRouter()


async def _get_store_and_menu_repo(user: User, db: AsyncSession):
    store_repo = StoreRepository(db)
    store = await store_repo.find_by_owner(user.id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store, MenuRepository(db)


# --- Categories ---


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    return await repo.list_categories(store.id)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreateRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    return await repo.create_category(store_id=store.id, name=body.name, sort_order=body.sort_order)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdateRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    category = await repo.find_category(category_id, store.id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return await repo.update_category(category, **body.model_dump(exclude_unset=True))


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    category = await repo.find_category(category_id, store.id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    await repo.delete_category(category)
    return MessageResponse(message="Category deleted")


# --- Items ---


@router.get("/items", response_model=list[MenuItemResponse])
async def list_items(
    category_id: uuid.UUID | None = None,
    item_status: MenuItemStatus | None = None,
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    return await repo.list_items(
        store.id, category_id=category_id, status=item_status, offset=offset, limit=limit
    )


@router.post("/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: MenuItemCreateRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)

    if body.category_id:
        category = await repo.find_category(body.category_id, store.id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    return await repo.create_item(store_id=store.id, **body.model_dump())


@router.put("/items/{item_id}", response_model=MenuItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: MenuItemUpdateRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    item = await repo.find_item(item_id, store.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return await repo.update_item(item, **body.model_dump(exclude_unset=True))


@router.delete("/items/{item_id}", response_model=MessageResponse)
async def delete_item(
    item_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    item = await repo.find_item(item_id, store.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    if item.image_url:
        delete_image(item.image_url)
    await repo.delete_item(item)
    return MessageResponse(message="Menu item deleted")


@router.post("/items/{item_id}/image", response_model=MenuItemResponse)
async def upload_item_image(
    item_id: uuid.UUID,
    file: UploadFile,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    item = await repo.find_item(item_id, store.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    content = await file.read()
    error = validate_image(file.content_type, len(content))
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    if item.image_url:
        delete_image(item.image_url)

    image_url, thumb_url = upload_image(content, f"stores/{store.id}/items")
    return await repo.update_item(item, image_url=image_url, thumbnail_url=thumb_url)


@router.patch("/items/{item_id}/status", response_model=MenuItemResponse)
async def update_item_status(
    item_id: uuid.UUID,
    body: MenuItemStatusRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    item = await repo.find_item(item_id, store.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return await repo.update_item(item, status=body.status)
