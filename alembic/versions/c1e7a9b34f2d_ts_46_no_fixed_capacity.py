"""TS-46 no_fixed_capacity for products_catalog

Revision ID: c1e7a9b34f2d
Revises: e464f7703e20
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'c1e7a9b34f2d'
down_revision: Union[str, None] = 'e464f7703e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('products_catalog', schema=None) as batch_op:
        batch_op.add_column(sa.Column('no_fixed_capacity', sa.Boolean(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('products_catalog', schema=None) as batch_op:
        batch_op.drop_column('no_fixed_capacity')
