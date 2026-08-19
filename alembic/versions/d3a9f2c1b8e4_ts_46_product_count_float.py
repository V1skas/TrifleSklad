"""TS-46 product count as float (fractional unit capacity)

Revision ID: d3a9f2c1b8e4
Revises: c1e7a9b34f2d
Create Date: 2026-07-22 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'd3a9f2c1b8e4'
down_revision: Union[str, None] = 'c1e7a9b34f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column(
            'count',
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column(
            'count',
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
