"""update order status enum and add order_cancelled notification type

Revision ID: b1e2f3a4c5d6
Revises: 90a1132e493b
Create Date: 2026-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1e2f3a4c5d6"
down_revision: Union[str, None] = "90a1132e493b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- OrderStatus enum: rename CONFIRMED->RECEIVED, READY->SENT, remove PICKED_UP ---

    # 1. Create new enum type with desired values (UPPERCASE to match existing convention)
    op.execute("""
        CREATE TYPE orderstatus_new AS ENUM (
            'PENDING', 'RECEIVED', 'PREPARING', 'SENT', 'DELIVERED', 'CANCELLED'
        )
    """)

    # 2. Convert column to text, normalize to uppercase, migrate values, cast to new enum
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE text USING status::text")
    op.execute("UPDATE orders SET status = upper(status)")
    op.execute("UPDATE orders SET status = 'RECEIVED' WHERE status = 'CONFIRMED'")
    op.execute("UPDATE orders SET status = 'SENT' WHERE status = 'READY'")
    op.execute("UPDATE orders SET status = 'SENT' WHERE status = 'PICKED_UP'")
    op.execute(
        "ALTER TABLE orders ALTER COLUMN status TYPE orderstatus_new"
        " USING status::orderstatus_new"
    )

    # 3. Drop old type and rename new
    op.execute("DROP TYPE orderstatus")
    op.execute("ALTER TYPE orderstatus_new RENAME TO orderstatus")

    # --- Add ORDER_CANCELLED to NotificationType enum ---
    # NotificationType already uses UPPERCASE names in DB
    op.execute("""
        CREATE TYPE notificationtype_new AS ENUM (
            'STORE_REGISTERED', 'STORE_APPROVED', 'STORE_REJECTED',
            'ORDER_NEW', 'ORDER_STATUS', 'ORDER_CANCELLED'
        )
    """)
    op.execute(
        "ALTER TABLE notifications ALTER COLUMN type TYPE text USING type::text"
    )
    op.execute("UPDATE notifications SET type = upper(type)")
    op.execute(
        "ALTER TABLE notifications ALTER COLUMN type TYPE notificationtype_new"
        " USING type::notificationtype_new"
    )
    op.execute("DROP TYPE notificationtype")
    op.execute("ALTER TYPE notificationtype_new RENAME TO notificationtype")


def downgrade() -> None:
    # Recreate old OrderStatus enum
    op.execute("""
        CREATE TYPE orderstatus_old AS ENUM (
            'PENDING', 'CONFIRMED', 'PREPARING', 'READY',
            'PICKED_UP', 'DELIVERED', 'CANCELLED'
        )
    """)
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE text USING status::text")
    op.execute("UPDATE orders SET status = 'CONFIRMED' WHERE status = 'RECEIVED'")
    op.execute("UPDATE orders SET status = 'READY' WHERE status = 'SENT'")
    op.execute(
        "ALTER TABLE orders ALTER COLUMN status TYPE orderstatus_old"
        " USING status::orderstatus_old"
    )
    op.execute("DROP TYPE orderstatus")
    op.execute("ALTER TYPE orderstatus_old RENAME TO orderstatus")

    # Recreate old NotificationType enum (without ORDER_CANCELLED)
    op.execute("""
        CREATE TYPE notificationtype_old AS ENUM (
            'STORE_REGISTERED', 'STORE_APPROVED', 'STORE_REJECTED',
            'ORDER_NEW', 'ORDER_STATUS'
        )
    """)
    op.execute(
        "ALTER TABLE notifications ALTER COLUMN type TYPE text USING type::text"
    )
    op.execute("DELETE FROM notifications WHERE type = 'ORDER_CANCELLED'")
    op.execute(
        "ALTER TABLE notifications ALTER COLUMN type TYPE notificationtype_old"
        " USING type::notificationtype_old"
    )
    op.execute("DROP TYPE notificationtype")
    op.execute("ALTER TYPE notificationtype_old RENAME TO notificationtype")
