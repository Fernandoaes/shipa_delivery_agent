"""unique constraint on customers.primary_phone

Revision ID: c3a7f1e2b9d4
Revises: 1fd8583ad65a
Create Date: 2026-06-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a7f1e2b9d4'
down_revision: Union[str, Sequence[str], None] = '1fd8583ad65a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fail loudly with the offending numbers rather than a cryptic IntegrityError.
    bind = op.get_bind()
    dupes = bind.execute(
        sa.text(
            "SELECT primary_phone, count(*) AS n "
            "FROM customers GROUP BY primary_phone HAVING count(*) > 1 ORDER BY n DESC"
        )
    ).fetchall()
    if dupes:
        listed = ", ".join(f"{row.primary_phone} (x{row.n})" for row in dupes)
        raise RuntimeError(
            f"Cannot add UNIQUE(primary_phone): {len(dupes)} duplicated number(s) must be "
            f"merged/deduped first: {listed}"
        )

    op.create_unique_constraint("uq_customers_primary_phone", "customers", ["primary_phone"])


def downgrade() -> None:
    op.drop_constraint("uq_customers_primary_phone", "customers", type_="unique")
