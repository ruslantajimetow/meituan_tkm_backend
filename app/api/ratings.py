import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import upload_image, validate_image
from app.middleware.auth import get_current_user, require_role
from app.models.menu_item import MenuItem
from app.models.notification import NotificationType
from app.models.store import Store, StoreStatus
from app.models.user import User, UserRole
from app.repositories.rating_repository import RatingRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.rating import (
    MerchantReplyRequest,
    ProductReviewCreateRequest,
    ProductReviewResponse,
    ProductReviewSummary,
    StoreProductReviewResponse,
    StoreRatingCreateRequest,
    StoreRatingResponse,
    StoreRatingSummary,
)
from app.services.notification_service import NotificationService

router = APIRouter()


# --- Store Ratings ---


@router.post("/stores/{store_id}/rating", response_model=StoreRatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_store(
    store_id: uuid.UUID,
    body: StoreRatingCreateRequest,
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.status == StoreStatus.APPROVED)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    repo = RatingRepository(db)
    rating = await repo.upsert_store_rating(user_id=user.id, store_id=store_id, stars=body.stars)

    # Notify store owner
    notifier = NotificationService(db)
    await notifier.notify(
        user_id=store.owner_id,
        notification_type=NotificationType.STORE_RATED,
        title="New Store Rating",
        body=f"{user.full_name} rated your store {body.stars} stars",
        data={"store_id": str(store_id), "stars": body.stars},
    )

    return rating


@router.get("/stores/{store_id}/rating", response_model=StoreRatingSummary)
async def get_store_rating_summary(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    avg_stars, total = await RatingRepository(db).get_store_summary(store_id)
    return StoreRatingSummary(average_stars=round(avg_stars, 1), total_ratings=total)


@router.get("/stores/{store_id}/rating/me", response_model=StoreRatingResponse | None)
async def get_my_store_rating(
    store_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RatingRepository(db).find_store_rating(user.id, store_id)


# --- Product Reviews ---


@router.post(
    "/products/{item_id}/review",
    response_model=ProductReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def review_product(
    item_id: uuid.UUID,
    body: ProductReviewCreateRequest,
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    repo = RatingRepository(db)
    review = await repo.upsert_product_review(
        user_id=user.id,
        menu_item_id=item_id,
        stars=body.stars,
        text=body.text,
    )

    # Notify store owner
    store_repo = StoreRepository(db)
    store = await store_repo.find_by_id(item.store_id)
    if store:
        notifier = NotificationService(db)
        await notifier.notify(
            user_id=store.owner_id,
            notification_type=NotificationType.PRODUCT_REVIEWED,
            title="New Product Review",
            body=f"{user.full_name} reviewed \"{item.name}\" — {body.stars} stars",
            data={
                "item_id": str(item_id),
                "item_name": item.name,
                "review_id": str(review.id),
                "stars": body.stars,
            },
        )

    return review


@router.post("/products/{item_id}/review/image", response_model=ProductReviewResponse)
async def upload_review_image(
    item_id: uuid.UUID,
    file: UploadFile,
    user: User = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    repo = RatingRepository(db)
    review = await repo.find_product_review(user.id, item_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found. Submit a review first.")

    content = await file.read()
    error = validate_image(file.content_type, len(content))
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    image_url, _ = upload_image(content, f"reviews/{item_id}/{user.id}")

    updated = await repo.upsert_product_review(
        user_id=user.id,
        menu_item_id=item_id,
        stars=review.stars,
        text=review.text,
        image_url=image_url,
    )
    return updated


@router.get("/products/{item_id}/reviews", response_model=list[ProductReviewResponse])
async def list_product_reviews(
    item_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await RatingRepository(db).list_product_reviews(item_id, offset=offset, limit=limit)


@router.get("/products/{item_id}/review/summary", response_model=ProductReviewSummary)
async def get_product_review_summary(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    avg_stars, total = await RatingRepository(db).get_product_summary(item_id)
    return ProductReviewSummary(average_stars=round(avg_stars, 1), total_reviews=total)


@router.get("/products/{item_id}/review/me", response_model=ProductReviewResponse | None)
async def get_my_product_review(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RatingRepository(db).find_product_review(user.id, item_id)


# --- Store Reviews (merchant view) ---


@router.get("/stores/{store_id}/reviews", response_model=list[StoreProductReviewResponse])
async def list_store_reviews(
    store_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    rows = await RatingRepository(db).list_store_reviews(store_id, offset=offset, limit=limit)
    return [
        StoreProductReviewResponse.model_validate({**review.__dict__, "item_name": item_name})
        for review, item_name in rows
    ]


# --- Merchant Reply ---


@router.post("/reviews/{review_id}/reply", response_model=ProductReviewResponse)
async def reply_to_review(
    review_id: uuid.UUID,
    body: MerchantReplyRequest,
    user: User = Depends(require_role(UserRole.MERCHANT)),
    db: AsyncSession = Depends(get_db),
):
    repo = RatingRepository(db)
    review = await repo.find_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    # Verify the review belongs to one of this merchant's items
    result = await db.execute(select(MenuItem).where(MenuItem.id == review.menu_item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    store_repo = StoreRepository(db)
    store = await store_repo.find_by_owner(user.id)
    if not store or item.store_id != store.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your product")

    updated_review = await repo.reply_to_review(review, body.text)

    # Notify the reviewer
    notifier = NotificationService(db)
    await notifier.notify(
        user_id=review.user_id,
        notification_type=NotificationType.REVIEW_REPLY,
        title=f"{store.name} replied to your review",
        body=body.text[:100],
        data={
            "item_id": str(item.id),
            "item_name": item.name,
            "review_id": str(review.id),
            "store_id": str(store.id),
        },
    )

    return updated_review
