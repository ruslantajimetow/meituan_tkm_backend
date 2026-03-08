import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu_category import MenuCategory
from app.models.menu_item import MenuItem, MenuItemStatus


class MenuRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    # --- Categories ---

    async def find_category(self, category_id: uuid.UUID, store_id: uuid.UUID) -> MenuCategory | None:
        result = await self._db.execute(
            select(MenuCategory).where(
                MenuCategory.id == category_id,
                MenuCategory.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_categories(self, store_id: uuid.UUID) -> list[MenuCategory]:
        result = await self._db.execute(
            select(MenuCategory)
            .where(MenuCategory.store_id == store_id)
            .order_by(MenuCategory.sort_order, MenuCategory.name)
        )
        return list(result.scalars().all())

    async def create_category(self, *, store_id: uuid.UUID, name: str, sort_order: int = 0) -> MenuCategory:
        category = MenuCategory(store_id=store_id, name=name, sort_order=sort_order)
        self._db.add(category)
        await self._db.flush()
        return category

    async def update_category(self, category: MenuCategory, **kwargs) -> MenuCategory:
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        merged_attrs = {
            "id": category.id,
            "store_id": category.store_id,
            "name": category.name,
            "sort_order": category.sort_order,
            "created_at": category.created_at,
            **update_data,
        }
        updated = MenuCategory(**merged_attrs)
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def delete_category(self, category: MenuCategory) -> None:
        await self._db.delete(category)
        await self._db.flush()

    # --- Items ---

    async def find_item(self, item_id: uuid.UUID, store_id: uuid.UUID) -> MenuItem | None:
        result = await self._db.execute(
            select(MenuItem).where(
                MenuItem.id == item_id,
                MenuItem.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_items(
        self,
        store_id: uuid.UUID,
        *,
        category_id: uuid.UUID | None = None,
        status: MenuItemStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[MenuItem]:
        query = (
            select(MenuItem)
            .where(MenuItem.store_id == store_id)
            .offset(offset)
            .limit(limit)
            .order_by(MenuItem.sort_order, MenuItem.name)
        )
        if category_id is not None:
            query = query.where(MenuItem.category_id == category_id)
        if status is not None:
            query = query.where(MenuItem.status == status)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def create_item(self, **kwargs) -> MenuItem:
        item = MenuItem(**kwargs)
        self._db.add(item)
        await self._db.flush()
        return item

    async def update_item(self, item: MenuItem, **kwargs) -> MenuItem:
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        merged_attrs = {
            "id": item.id,
            "store_id": item.store_id,
            "category_id": item.category_id,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "image_url": item.image_url,
            "thumbnail_url": item.thumbnail_url,
            "status": item.status,
            "sort_order": item.sort_order,
            "portion_size": item.portion_size,
            "is_spicy": item.is_spicy,
            "allergens": item.allergens,
            "weight": item.weight,
            "unit": item.unit,
            "sku": item.sku,
            "created_at": item.created_at,
            **update_data,
        }
        updated = MenuItem(**merged_attrs)
        merged = await self._db.merge(updated)
        await self._db.flush()
        return merged

    async def delete_item(self, item: MenuItem) -> None:
        await self._db.delete(item)
        await self._db.flush()
