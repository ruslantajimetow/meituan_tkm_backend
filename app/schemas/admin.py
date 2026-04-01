from pydantic import BaseModel

from app.models.store import StoreStatus
from app.schemas.auth import UserResponse
from app.schemas.store import StoreDocumentResponse, StoreResponse


class StoreStatusUpdateRequest(BaseModel):
    status: StoreStatus


class UserActiveUpdateRequest(BaseModel):
    is_active: bool


class AdminStoreDetailResponse(StoreResponse):
    """Extended store response for the admin detail view, including owner info and documents."""

    owner: UserResponse
    documents: list[StoreDocumentResponse]
