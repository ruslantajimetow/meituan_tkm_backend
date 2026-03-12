"""add ingredients, ratings, spice_level

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-03-11 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

spice_level_enum = postgresql.ENUM(
    "NO_SPICE", "LITTLE_SPICE", "NORMAL", "EXTRA_SPICE",
    name="spicelevel",
    create_type=False,
)


def upgrade() -> None:
    # Phase 1: Add ingredients column to menu_items
    op.add_column(
        "menu_items",
        sa.Column("ingredients", postgresql.ARRAY(sa.String(200)), nullable=True),
    )

    # Phase 2: Create store_ratings table
    op.create_table(
        "store_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "store_id", name="uq_store_rating_user_store"),
    )

    # Phase 2: Create product_reviews table
    op.create_table(
        "product_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("menu_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "menu_item_id", name="uq_product_review_user_item"),
    )

    # Phase 3: Add spice_level enum and column to order_items
    spice_level_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "order_items",
        sa.Column("spice_level", spice_level_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_items", "spice_level")
    spice_level_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_table("product_reviews")
    op.drop_table("store_ratings")
    op.drop_column("menu_items", "ingredients")
