import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu_category import MenuCategory
from app.models.menu_item import MenuItem, MenuItemImage, MenuItemStatus
from app.models.store import Store, StoreStatus


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
            select(MenuItem)
            .options(selectinload(MenuItem.images))
            .where(
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
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[MenuItem]:
        query = (
            select(MenuItem)
            .options(selectinload(MenuItem.images))
            .where(MenuItem.store_id == store_id)
            .offset(offset)
            .limit(limit)
            .order_by(MenuItem.sort_order, MenuItem.name)
        )
        if category_id is not None:
            query = query.where(MenuItem.category_id == category_id)
        if status is not None:
            query = query.where(MenuItem.status == status)
        if search:
            query = query.where(
                or_(
                    MenuItem.name.ilike(f"%{search}%"),
                    MenuItem.description.ilike(f"%{search}%"),
                )
            )
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def create_item(self, **kwargs) -> MenuItem:
        item = MenuItem(**kwargs)
        self._db.add(item)
        await self._db.flush()
        return await self.find_item(item.id, item.store_id)

    async def update_item(self, item: MenuItem, **kwargs) -> MenuItem:
        # Include all explicitly passed kwargs (even None) to allow clearing fields
        update_data = dict(kwargs)
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
            "ingredients": item.ingredients,
            "weight": item.weight,
            "unit": item.unit,
            "sku": item.sku,
            "created_at": item.created_at,
            **update_data,
        }
        updated = MenuItem(**merged_attrs)
        merged = await self._db.merge(updated)
        await self._db.flush()
        # Re-fetch with images loaded
        return await self.find_item(merged.id, merged.store_id)

    async def delete_item(self, item: MenuItem) -> None:
        await self._db.delete(item)
        await self._db.flush()

    # --- Item Images ---

    async def add_item_image(
        self,
        menu_item_id: uuid.UUID,
        image_url: str,
        thumbnail_url: str | None = None,
        sort_order: int = 0,
    ) -> MenuItemImage:
        image = MenuItemImage(
            menu_item_id=menu_item_id,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            sort_order=sort_order,
        )
        self._db.add(image)
        await self._db.flush()
        return image

    async def find_item_image(
        self, image_id: uuid.UUID, menu_item_id: uuid.UUID,
    ) -> MenuItemImage | None:
        result = await self._db.execute(
            select(MenuItemImage).where(
                MenuItemImage.id == image_id,
                MenuItemImage.menu_item_id == menu_item_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_item_images(self, menu_item_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(MenuItemImage)
            .where(MenuItemImage.menu_item_id == menu_item_id)
        )
        return result.scalar_one()

    async def delete_item_image(self, image: MenuItemImage) -> None:
        await self._db.delete(image)
        await self._db.flush()

    # --- Public search ---

    async def search_public_products(
        self, query: str, *, limit: int = 20,
    ) -> list[tuple[MenuItem, str]]:
        """Search active products across all approved stores.
        Returns list of (MenuItem, store_name) tuples.
        """
        pattern = f"%{query}%"
        search_filter = or_(
            MenuItem.name.ilike(pattern),
            MenuItem.description.ilike(pattern),
            func.array_to_string(MenuItem.ingredients, " ").ilike(pattern),
        )
        result = await self._db.execute(
            select(MenuItem, Store.name.label("store_name"))
            .join(Store, MenuItem.store_id == Store.id)
            .where(
                Store.status == StoreStatus.APPROVED,
                MenuItem.status == MenuItemStatus.ACTIVE,
                search_filter,
            )
            .order_by(MenuItem.name)
            .limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]
