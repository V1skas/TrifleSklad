"""users id_worker not null

Revision ID: 602eb9c51812
Revises: a1f2c8d94b60
Create Date: 2026-07-14 20:42:57.041046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '602eb9c51812'
down_revision: Union[str, None] = 'a1f2c8d94b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # existing_type обязателен: MySQL для CHANGE/MODIFY COLUMN требует явный тип
    # существующей колонки (на SQLite игнорируется). id_worker — Integer.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('id_worker',
               existing_type=sa.Integer(),
               nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('id_worker',
               existing_type=sa.Integer(),
               nullable=True)
