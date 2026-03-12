import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address


class AddressRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def list_by_user(self, user_id: uuid.UUID) -> list[Address]:
        result = await self._db.execute(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_id(self, address_id: uuid.UUID) -> Address | None:
        result = await self._db.execute(
            select(Address).where(Address.id == address_id)
        )
        return result.scalar_one_or_none()

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(Address).where(Address.user_id == user_id)
        )
        return len(result.scalars().all())

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        label: str,
        address_line: str,
        is_default: bool = False,
    ) -> Address:
        # If this is the first address or explicitly default, unset others
        existing_count = await self.count_by_user(user_id)
        should_be_default = is_default or existing_count == 0

        if should_be_default:
            await self._unset_all_defaults(user_id)

        address = Address(
            user_id=user_id,
            label=label,
            address_line=address_line,
            is_default=should_be_default,
        )
        self._db.add(address)
        await self._db.flush()
        return address

    async def update(
        self,
        address: Address,
        *,
        label: str | None = None,
        address_line: str | None = None,
    ) -> Address:
        updated = Address(
            id=address.id,
            user_id=address.user_id,
            label=label if label is not None else address.label,
            address_line=(
                address_line if address_line is not None else address.address_line
            ),
            is_default=address.is_default,
            created_at=address.created_at,
        )
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def delete(self, address: Address) -> None:
        was_default = address.is_default
        user_id = address.user_id
        await self._db.delete(address)
        await self._db.flush()

        # If deleted address was default, promote the next one
        if was_default:
            remaining = await self.list_by_user(user_id)
            if remaining:
                await self.set_default(user_id, remaining[0].id)

    async def set_default(
        self, user_id: uuid.UUID, address_id: uuid.UUID,
    ) -> Address | None:
        await self._unset_all_defaults(user_id)
        result = await self._db.execute(
            select(Address).where(
                Address.id == address_id, Address.user_id == user_id,
            )
        )
        address = result.scalar_one_or_none()
        if address:
            address.is_default = True
            await self._db.flush()
        return address

    async def _unset_all_defaults(self, user_id: uuid.UUID) -> None:
        await self._db.execute(
            update(Address)
            .where(Address.user_id == user_id, Address.is_default.is_(True))
            .values(is_default=False)
        )
