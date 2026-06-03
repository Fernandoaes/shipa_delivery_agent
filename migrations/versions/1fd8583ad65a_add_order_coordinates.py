"""add order coordinates

Revision ID: 1fd8583ad65a
Revises: a9e1dcce6457
Create Date: 2026-06-03 13:09:50.515425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fd8583ad65a'
down_revision: Union[str, Sequence[str], None] = 'a9e1dcce6457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("merchant_lat", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("merchant_lng", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("delivery_lat", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("delivery_lng", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_lng")
    op.drop_column("orders", "delivery_lat")
    op.drop_column("orders", "merchant_lng")
    op.drop_column("orders", "merchant_lat")
