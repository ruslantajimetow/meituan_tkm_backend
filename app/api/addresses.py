import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.repositories.address_repository import AddressRepository
from app.schemas.address import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=list[AddressResponse])
async def list_addresses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AddressRepository(db)
    return await repo.list_by_user(user.id)


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    body: AddressCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AddressRepository(db)
    return await repo.create(
        user_id=user.id,
        label=body.label,
        address_line=body.address_line,
        is_default=body.is_default,
    )


@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: uuid.UUID,
    body: AddressUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AddressRepository(db)
    address = await repo.find_by_id(address_id)
    if not address or address.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found",
        )
    return await repo.update(
        address, label=body.label, address_line=body.address_line,
    )


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AddressRepository(db)
    address = await repo.find_by_id(address_id)
    if not address or address.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found",
        )
    await repo.delete(address)


@router.patch("/{address_id}/default", response_model=AddressResponse)
async def set_default_address(
    address_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AddressRepository(db)
    address = await repo.find_by_id(address_id)
    if not address or address.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found",
        )
    updated = await repo.set_default(user.id, address_id)
    return updated
