import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AddressCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    address_line: str = Field(min_length=1, max_length=500)
    is_default: bool = False


class AddressUpdateRequest(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    address_line: str | None = Field(None, min_length=1, max_length=500)


class AddressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    label: str
    address_line: str
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
