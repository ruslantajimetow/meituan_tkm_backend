"""add_print_server_url_to_stores

Revision ID: a1b2c3d4e5f6
Revises: 6a0873425466
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6a0873425466'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stores', sa.Column('print_server_url', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('stores', 'print_server_url')
