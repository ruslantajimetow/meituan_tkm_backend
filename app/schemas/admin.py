from pydantic import BaseModel

from app.models.store import StoreStatus


class StoreStatusUpdateRequest(BaseModel):
    status: StoreStatus


class UserActiveUpdateRequest(BaseModel):
    is_active: bool
