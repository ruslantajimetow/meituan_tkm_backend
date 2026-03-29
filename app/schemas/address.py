import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AddressCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    address_line: str = Field(min_length=1, max_length=500)
    is_default: bool = False
    flat_number: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def lat_lng_pair(self) -> "AddressCreateRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be provided or both omitted")
        return self


class AddressUpdateRequest(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    address_line: str | None = Field(None, min_length=1, max_length=500)
    flat_number: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def lat_lng_pair(self) -> "AddressUpdateRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be provided or both omitted")
        return self


class AddressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    label: str
    address_line: str
    flat_number: str | None
    house_number: str | None
    latitude: float | None
    longitude: float | None
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
