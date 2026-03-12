"""add customer_phone to orders

Revision ID: c2d3e4f5a6b7
Revises: b1e2f3a4c5d6
Create Date: 2026-03-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1e2f3a4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("customer_phone", sa.String(20), nullable=True),
    )
    # Backfill existing orders with empty string
    op.execute("UPDATE orders SET customer_phone = '' WHERE customer_phone IS NULL")
    op.alter_column("orders", "customer_phone", nullable=False)


def downgrade() -> None:
    op.drop_column("orders", "customer_phone")
