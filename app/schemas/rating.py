import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StoreRatingCreateRequest(BaseModel):
    stars: int = Field(ge=1, le=5)


class StoreRatingResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    store_id: uuid.UUID
    stars: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreRatingSummary(BaseModel):
    average_stars: float
    total_ratings: int


class ProductReviewCreateRequest(BaseModel):
    stars: int = Field(ge=1, le=5)
    text: str = Field(min_length=1, max_length=2000)


class ProductReviewResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    menu_item_id: uuid.UUID
    stars: int
    text: str
    image_url: str | None
    merchant_reply: str | None = None
    replied_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductReviewSummary(BaseModel):
    average_stars: float
    total_reviews: int


class MerchantReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class StoreProductReviewResponse(ProductReviewResponse):
    """ProductReview enriched with the menu item name — used in merchant review list."""
    item_name: str
