"""TS-41 session sliding window + permissions_version

Revision ID: a1f2c8d94b60
Revises: b1e2c4a9f6d3
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'a1f2c8d94b60'
down_revision: Union[str, None] = 'b1e2c4a9f6d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('permissions_version', sa.Integer(), server_default=sa.text('0'), nullable=False))

    with op.batch_alter_table('auth_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))
        batch_op.add_column(sa.Column('last_activity_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))

    # Перехід на нову модель сесії (cookie + ковзне вікно): існуючі токени не
    # мають valid expires_at (тільки що доданий стовпець отримав CURRENT_TIMESTAMP,
    # тобто вже "протермінований" за замовчуванням) — примусово чистимо, усі
    # користувачі перелогиняться один раз.
    op.execute("DELETE FROM auth_tokens")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('auth_tokens', schema=None) as batch_op:
        batch_op.drop_column('last_activity_at')
        batch_op.drop_column('expires_at')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('permissions_version')
