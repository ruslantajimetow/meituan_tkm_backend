"""add review reply and notification types

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add merchant_reply and replied_at to product_reviews
    op.add_column("product_reviews", sa.Column("merchant_reply", sa.Text(), nullable=True))
    op.add_column(
        "product_reviews",
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add new notification types to the enum
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'store_rated'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'product_reviewed'")


def downgrade() -> None:
    op.drop_column("product_reviews", "replied_at")
    op.drop_column("product_reviews", "merchant_reply")
    # Note: PostgreSQL doesn't support removing enum values easily
