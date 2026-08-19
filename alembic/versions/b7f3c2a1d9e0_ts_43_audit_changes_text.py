"""TS-43 audit_log.changes to TEXT (MySQL VARCHAR overflow)

Revision ID: b7f3c2a1d9e0
Revises: 3b24eadfcf46
Create Date: 2026-08-19 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7f3c2a1d9e0'
down_revision: Union[str, None] = '3b24eadfcf46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # `changes` зберігає JSON аудиту, який може бути великим (напр. правка ролі
    # з десятками прав). AutoString на MySQL — VARCHAR(255), тому переповнюється
    # («Data too long for column 'changes'»). Переводимо на TEXT.
    # existing_type обов'язковий: MySQL для CHANGE/MODIFY COLUMN вимагає явний
    # тип наявної колонки (на SQLite ігнорується).
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.alter_column(
            'changes',
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.alter_column(
            'changes',
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
