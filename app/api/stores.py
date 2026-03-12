import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import delete_image, upload_image, validate_image
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.repositories.store_repository import StoreRepository
from app.schemas.auth import MessageResponse
from app.schemas.store import (
    StoreImageResponse,
    StoreResponse,
    StoreUpdateRequest,
)

router = APIRouter()


async def _get_merchant_store(user: User, db: AsyncSession):
    repo = StoreRepository(db)
    store = await repo.find_by_owner(user.id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store, repo


@router.get("/me", response_model=StoreResponse)
async def get_my_store(
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, _ = await _get_merchant_store(user, db)
    return store


@router.put("/me", response_model=StoreResponse)
async def update_my_store(
    body: StoreUpdateRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_merchant_store(user, db)
    update_data = body.model_dump(exclude_unset=True)

    # Validate that opening_time and closing_time come as a pair
    has_opening = "opening_time" in update_data
    has_closing = "closing_time" in update_data
    if has_opening != has_closing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both opening_time and closing_time must be provided together",
        )

    updated = await repo.update(store, **update_data)
    return updated


@router.post("/me/logo", response_model=StoreResponse)
async def upload_logo(
    file: UploadFile,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_merchant_store(user, db)
    content = await file.read()
    error = validate_image(file.content_type, len(content))
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    if store.logo_url:
        delete_image(store.logo_url)

    image_url, _ = upload_image(content, f"stores/{store.id}/logo")
    updated = await repo.update(store, logo_url=image_url)
    return updated


@router.post("/me/cover", response_model=StoreResponse)
async def upload_cover(
    file: UploadFile,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_merchant_store(user, db)
    content = await file.read()
    error = validate_image(file.content_type, len(content))
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    if store.cover_image_url:
        delete_image(store.cover_image_url)

    image_url, _ = upload_image(content, f"stores/{store.id}/cover")
    updated = await repo.update(store, cover_image_url=image_url)
    return updated


@router.post("/me/images", response_model=StoreImageResponse)
async def add_gallery_image(
    file: UploadFile,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_merchant_store(user, db)
    content = await file.read()
    error = validate_image(file.content_type, len(content))
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    image_url, thumb_url = upload_image(content, f"stores/{store.id}/gallery")
    image = await repo.add_image(store.id, image_url, thumb_url)
    return image


@router.delete("/me/images/{image_id}", response_model=MessageResponse)
async def delete_gallery_image(
    image_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    store, repo = await _get_merchant_store(user, db)
    image = await repo.find_image(image_id, store.id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    delete_image(image.image_url)
    await repo.delete_image(image)
    return MessageResponse(message="Image deleted")
