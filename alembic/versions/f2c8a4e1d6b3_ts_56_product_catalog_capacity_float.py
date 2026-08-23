"""TS-56 product catalog capacity as float (fractional capacity)

Revision ID: f2c8a4e1d6b3
Revises: b7f3c2a1d9e0
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'f2c8a4e1d6b3'
down_revision: Union[str, None] = 'b7f3c2a1d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('products_catalog', schema=None) as batch_op:
        batch_op.alter_column(
            'capacity',
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('products_catalog', schema=None) as batch_op:
        batch_op.alter_column(
            'capacity',
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
