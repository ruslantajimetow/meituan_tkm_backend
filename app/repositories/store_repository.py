import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.store import MerchantType, Store, StoreImage, StoreStatus
from app.services.store_hours import current_tmt_time


class StoreRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_id(self, store_id: uuid.UUID) -> Store | None:
        result = await self._db.execute(
            select(Store)
            .options(selectinload(Store.images))
            .where(Store.id == store_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id_with_details(self, store_id: uuid.UUID) -> Store | None:
        """Load store with images, documents, and owner — for the admin detail view."""
        from app.models.user import User

        result = await self._db.execute(
            select(Store)
            .options(
                selectinload(Store.images),
                selectinload(Store.documents),
                selectinload(Store.owner),
            )
            .where(Store.id == store_id)
        )
        return result.scalar_one_or_none()

    async def find_by_owner(self, owner_id: uuid.UUID) -> Store | None:
        result = await self._db.execute(
            select(Store)
            .options(selectinload(Store.images))
            .where(Store.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Store:
        store = Store(**kwargs)
        self._db.add(store)
        await self._db.flush()
        # Re-fetch with images loaded
        return await self.find_by_id(store.id)

    async def update(self, store: Store, **kwargs) -> Store:
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        merged_attrs = {
            "id": store.id,
            "owner_id": store.owner_id,
            "merchant_type": store.merchant_type,
            "name": store.name,
            "description": store.description,
            "phone": store.phone,
            "address": store.address,
            "latitude": store.latitude,
            "longitude": store.longitude,
            "logo_url": store.logo_url,
            "cover_image_url": store.cover_image_url,
            "status": store.status,
            "is_open": store.is_open,
            "opening_time": store.opening_time,
            "closing_time": store.closing_time,
            "min_order": store.min_order,
            "delivery_fee": store.delivery_fee,
            "cuisine_type": store.cuisine_type,
            "average_prep_time": store.average_prep_time,
            "has_dine_in": store.has_dine_in,
            "store_category": store.store_category,
            "has_delivery_only": store.has_delivery_only,
            "created_at": store.created_at,
            **update_data,
        }
        updated = Store(**merged_attrs)
        merged = await self._db.merge(updated)
        await self._db.flush()
        return await self.find_by_id(merged.id)

    async def add_image(
        self, store_id: uuid.UUID, image_url: str, thumbnail_url: str | None = None, sort_order: int = 0
    ) -> StoreImage:
        image = StoreImage(
            store_id=store_id,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            sort_order=sort_order,
        )
        self._db.add(image)
        await self._db.flush()
        return image

    async def find_image(self, image_id: uuid.UUID, store_id: uuid.UUID) -> StoreImage | None:
        result = await self._db.execute(
            select(StoreImage).where(
                StoreImage.id == image_id,
                StoreImage.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_image(self, image: StoreImage) -> None:
        await self._db.delete(image)
        await self._db.flush()

    async def list_stores(
        self,
        *,
        status: StoreStatus | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Store]:
        query = (
            select(Store)
            .options(selectinload(Store.images))
            .offset(offset)
            .limit(limit)
            .order_by(Store.created_at.desc())
        )
        if status is not None:
            query = query.where(Store.status == status)
        if search:
            query = query.where(Store.name.ilike(f"%{search}%"))
        result = await self._db.execute(query)
        return list(result.scalars().all())

    # --- Public browsing ---

    def _public_filters(
        self,
        *,
        merchant_type: MerchantType | None = None,
        search: str | None = None,
        cuisine_type: str | None = None,
        store_category: str | None = None,
    ) -> list:
        filters = [Store.status == StoreStatus.APPROVED]
        if merchant_type is not None:
            filters.append(Store.merchant_type == merchant_type)
        if search:
            filters.append(Store.name.ilike(f"%{search}%"))
        if cuisine_type:
            filters.append(Store.cuisine_type == cuisine_type)
        if store_category:
            filters.append(Store.store_category == store_category)
        return filters

    async def list_distinct_categories(self, merchant_type: MerchantType) -> list[str]:
        """Return distinct non-null category values for approved stores of a given type."""
        col = Store.cuisine_type if merchant_type == MerchantType.RESTAURANT else Store.store_category
        result = await self._db.execute(
            select(col)
            .where(Store.status == StoreStatus.APPROVED, col.isnot(None))
            .distinct()
            .order_by(col)
        )
        return [row[0] for row in result.all()]

    async def list_public(
        self,
        *,
        merchant_type: MerchantType | None = None,
        search: str | None = None,
        cuisine_type: str | None = None,
        store_category: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Store]:
        filters = self._public_filters(
            merchant_type=merchant_type,
            search=search,
            cuisine_type=cuisine_type,
            store_category=store_category,
        )
        now = current_tmt_time()

        # Compute open/closed at SQL level for ordering
        # Normal hours: opening <= now < closing
        normal_open = and_(
            Store.opening_time <= now,
            Store.closing_time > now,
            Store.opening_time <= Store.closing_time,
        )
        # Overnight hours: now >= opening OR now < closing
        overnight_open = and_(
            Store.opening_time > Store.closing_time,
            (Store.opening_time <= now) | (Store.closing_time > now),
        )
        has_hours = and_(
            Store.opening_time.isnot(None),
            Store.closing_time.isnot(None),
        )
        is_open_expr = case(
            (and_(has_hours, normal_open | overnight_open), 1),
            else_=0,
        )

        query = (
            select(Store)
            .options(selectinload(Store.images))
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(is_open_expr.desc(), Store.name)
        )
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def count_public(
        self,
        *,
        merchant_type: MerchantType | None = None,
        search: str | None = None,
        cuisine_type: str | None = None,
        store_category: str | None = None,
    ) -> int:
        filters = self._public_filters(
            merchant_type=merchant_type,
            search=search,
            cuisine_type=cuisine_type,
            store_category=store_category,
        )
        query = select(func.count()).select_from(Store).where(*filters)
        result = await self._db.execute(query)
        return result.scalar_one()

    async def list_nearby(
        self,
        *,
        lat: float,
        lng: float,
        merchant_type: MerchantType | None = None,
        search: str | None = None,
        cuisine_type: str | None = None,
        store_category: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[tuple[Store, float | None]]:
        filters = self._public_filters(
            merchant_type=merchant_type,
            search=search,
            cuisine_type=cuisine_type,
            store_category=store_category,
        )

        # Haversine distance expression (km). Clamp to [-1,1] to avoid acos domain errors.
        haversine = (
            6371.0
            * func.acos(
                func.least(
                    1.0,
                    func.greatest(
                        -1.0,
                        func.cos(func.radians(lat))
                        * func.cos(func.radians(Store.latitude))
                        * func.cos(func.radians(Store.longitude) - func.radians(lng))
                        + func.sin(func.radians(lat))
                        * func.sin(func.radians(Store.latitude)),
                    ),
                )
            )
        ).label("distance_km")

        # Stores without coordinates sort last
        has_coords = case((Store.latitude.is_(None), 1), else_=0)

        query = (
            select(Store, haversine)
            .options(selectinload(Store.images))
            .where(*filters)
            .order_by(has_coords, haversine)
            .offset(offset)
            .limit(limit)
        )

        result = await self._db.execute(query)
        rows = result.all()
        return [(row[0], float(row[1]) if row[1] is not None else None) for row in rows]

    async def count_nearby(
        self,
        *,
        lat: float,
        lng: float,
        merchant_type: MerchantType | None = None,
        search: str | None = None,
        cuisine_type: str | None = None,
        store_category: str | None = None,
    ) -> int:
        filters = self._public_filters(
            merchant_type=merchant_type,
            search=search,
            cuisine_type=cuisine_type,
            store_category=store_category,
        )
        query = select(func.count()).select_from(Store).where(*filters)
        result = await self._db.execute(query)
        return result.scalar_one()

    async def find_public(self, store_id: uuid.UUID) -> Store | None:
        result = await self._db.execute(
            select(Store)
            .options(selectinload(Store.images))
            .where(Store.id == store_id, Store.status == StoreStatus.APPROVED)
        )
        return result.scalar_one_or_none()
