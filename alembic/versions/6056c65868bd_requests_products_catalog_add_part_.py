"""requests_products_catalog add part_amount

Revision ID: 6056c65868bd
Revises: ec12f9b0adc4
Create Date: 2026-06-07 11:35:17.403930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '6056c65868bd'
down_revision: Union[str, None] = 'ec12f9b0adc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_column('requests_products_catalog', 'part_amount'):
        with op.batch_alter_table('requests_products_catalog', schema=None) as batch_op:
            batch_op.add_column(sa.Column('part_amount', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    if _has_column('requests_products_catalog', 'part_amount'):
        with op.batch_alter_table('requests_products_catalog', schema=None) as batch_op:
            batch_op.drop_column('part_amount')
