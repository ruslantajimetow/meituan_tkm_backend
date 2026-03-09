from pydantic import BaseModel, EmailStr, Field


class UpdateEmailRequest(BaseModel):
    email: EmailStr


class UpdatePhoneRequest(BaseModel):
    phone: str = Field(pattern=r"^\+993\d{8}$")


class BindPhoneVerifyRequest(BaseModel):
    phone: str = Field(pattern=r"^\+993\d{8}$")
    code: str = Field(min_length=6, max_length=6)
