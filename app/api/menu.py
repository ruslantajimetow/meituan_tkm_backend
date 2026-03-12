import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import delete_image, upload_image, validate_image
from app.middleware.auth import require_role
from app.models.menu_item import MenuItemStatus
from app.models.store import MerchantType
from app.models.user import User, UserRole
from app.repositories.menu_repository import MenuRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.auth import MessageResponse
from app.schemas.menu import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    MenuItemCreateRequest,
    MenuItemImageResponse,
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
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    return await repo.list_items(
        store.id, category_id=category_id, status=item_status, search=search,
        offset=offset, limit=limit,
    )


RESTAURANT_ONLY_FIELDS = {"portion_size", "is_spicy", "allergens", "ingredients"}
STORE_ONLY_FIELDS = {"weight", "unit", "sku"}


def _strip_type_fields(data: dict, merchant_type: MerchantType) -> dict:
    """Strip fields that don't belong to the merchant type."""
    if merchant_type == MerchantType.STORE:
        return {k: v for k, v in data.items() if k not in RESTAURANT_ONLY_FIELDS}
    return {k: v for k, v in data.items() if k not in STORE_ONLY_FIELDS}


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

    item_data = _strip_type_fields(body.model_dump(), store.merchant_type)
    return await repo.create_item(store_id=store.id, **item_data)


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
    update_data = _strip_type_fields(body.model_dump(exclude_unset=True), store.merchant_type)
    return await repo.update_item(item, **update_data)


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


MAX_ITEM_IMAGES = 5
MIN_ITEM_IMAGES_FOR_ACTIVE = 3


@router.post(
    "/items/{item_id}/image",
    response_model=MenuItemImageResponse,
    status_code=status.HTTP_201_CREATED,
)
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

    image_count = await repo.count_item_images(item_id)
    if image_count >= MAX_ITEM_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_ITEM_IMAGES} images per product",
        )

    content = await file.read()
    error = validate_image(file.content_type, len(content))
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    image_url, thumb_url = upload_image(content, f"stores/{store.id}/items/{item_id}")
    image = await repo.add_item_image(item_id, image_url, thumb_url, sort_order=image_count)

    # Keep legacy fields in sync with the first image
    if image_count == 0:
        await repo.update_item(item, image_url=image_url, thumbnail_url=thumb_url)

    return image


@router.delete("/items/{item_id}/images/{image_id}", response_model=MessageResponse)
async def delete_item_image(
    item_id: uuid.UUID,
    image_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_store_and_menu_repo(user, db)
    item = await repo.find_item(item_id, store.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    image = await repo.find_item_image(image_id, item_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    delete_image(image.image_url)
    await repo.delete_item_image(image)

    # Update legacy fields: set to first remaining image or clear
    remaining = await repo.count_item_images(item_id)
    if remaining == 0:
        await repo.update_item(item, image_url=None, thumbnail_url=None)

    return MessageResponse(message="Image deleted")


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

    if body.status == MenuItemStatus.ACTIVE:
        image_count = await repo.count_item_images(item_id)
        if image_count < MIN_ITEM_IMAGES_FOR_ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"At least {MIN_ITEM_IMAGES_FOR_ACTIVE} images required to activate",
            )

    return await repo.update_item(item, status=body.status)
