import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rating import ProductReview, StoreRating


class RatingRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    # --- Store Ratings ---

    async def find_store_rating(self, user_id: uuid.UUID, store_id: uuid.UUID) -> StoreRating | None:
        result = await self._db.execute(
            select(StoreRating).where(
                StoreRating.user_id == user_id,
                StoreRating.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_store_rating(self, *, user_id: uuid.UUID, store_id: uuid.UUID, stars: int) -> StoreRating:
        existing = await self.find_store_rating(user_id, store_id)
        if existing:
            updated = StoreRating(
                id=existing.id,
                user_id=existing.user_id,
                store_id=existing.store_id,
                stars=stars,
                created_at=existing.created_at,
            )
            merged = await self._db.merge(updated)
            await self._db.flush()
            return merged
        rating = StoreRating(user_id=user_id, store_id=store_id, stars=stars)
        self._db.add(rating)
        await self._db.flush()
        return rating

    async def get_store_summary(self, store_id: uuid.UUID) -> tuple[float, int]:
        result = await self._db.execute(
            select(
                func.coalesce(func.avg(StoreRating.stars), 0),
                func.count(),
            ).where(StoreRating.store_id == store_id)
        )
        row = result.one()
        return float(row[0]), row[1]

    # --- Product Reviews ---

    async def find_product_review(self, user_id: uuid.UUID, menu_item_id: uuid.UUID) -> ProductReview | None:
        result = await self._db.execute(
            select(ProductReview).where(
                ProductReview.user_id == user_id,
                ProductReview.menu_item_id == menu_item_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_review_by_id(self, review_id: uuid.UUID) -> ProductReview | None:
        result = await self._db.execute(
            select(ProductReview).where(ProductReview.id == review_id)
        )
        return result.scalar_one_or_none()

    async def upsert_product_review(
        self,
        *,
        user_id: uuid.UUID,
        menu_item_id: uuid.UUID,
        stars: int,
        text: str,
        image_url: str | None = None,
    ) -> ProductReview:
        existing = await self.find_product_review(user_id, menu_item_id)
        if existing:
            updated = ProductReview(
                id=existing.id,
                user_id=existing.user_id,
                menu_item_id=existing.menu_item_id,
                stars=stars,
                text=text,
                image_url=image_url or existing.image_url,
                merchant_reply=existing.merchant_reply,
                replied_at=existing.replied_at,
                created_at=existing.created_at,
            )
            merged = await self._db.merge(updated)
            await self._db.flush()
            return merged
        review = ProductReview(
            user_id=user_id,
            menu_item_id=menu_item_id,
            stars=stars,
            text=text,
            image_url=image_url,
        )
        self._db.add(review)
        await self._db.flush()
        return review

    async def reply_to_review(self, review: ProductReview, reply_text: str) -> ProductReview:
        updated = ProductReview(
            id=review.id,
            user_id=review.user_id,
            menu_item_id=review.menu_item_id,
            stars=review.stars,
            text=review.text,
            image_url=review.image_url,
            merchant_reply=reply_text,
            replied_at=datetime.now(UTC),
            created_at=review.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def list_product_reviews(
        self,
        menu_item_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ProductReview]:
        result = await self._db.execute(
            select(ProductReview)
            .where(ProductReview.menu_item_id == menu_item_id)
            .order_by(ProductReview.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_product_summary(self, menu_item_id: uuid.UUID) -> tuple[float, int]:
        result = await self._db.execute(
            select(
                func.coalesce(func.avg(ProductReview.stars), 0),
                func.count(),
            ).where(ProductReview.menu_item_id == menu_item_id)
        )
        row = result.one()
        return float(row[0]), row[1]
