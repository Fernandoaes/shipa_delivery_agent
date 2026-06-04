"""add order delivery tracking

Revision ID: b2c4e6a8d013
Revises: c3a7f1e2b9d4
Create Date: 2026-06-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c4e6a8d013'
down_revision: Union[str, Sequence[str], None] = 'c3a7f1e2b9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("sla_due_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "sla_due_at")
    op.drop_column("orders", "delivered_at")
    op.drop_column("orders", "attempt_count")
