"""TS-47 is_default for nds_rates + client_info for sales

Revision ID: a3f7d21c9e04
Revises: 602eb9c51812
Create Date: 2026-07-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'a3f7d21c9e04'
down_revision: Union[str, None] = '602eb9c51812'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('nds_rates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_default', sa.Boolean(), server_default=sa.text('0'), nullable=False))

    with op.batch_alter_table('sales', schema=None) as batch_op:
        batch_op.add_column(sa.Column('client_info', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('sales', schema=None) as batch_op:
        batch_op.drop_column('client_info')

    with op.batch_alter_table('nds_rates', schema=None) as batch_op:
        batch_op.drop_column('is_default')
