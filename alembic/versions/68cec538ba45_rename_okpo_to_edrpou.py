"""rename suppliers.okpo to edrpou

Revision ID: 68cec538ba45
Revises: 67f6c4eed5e0
Create Date: 2026-05-31 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = '68cec538ba45'
down_revision: Union[str, None] = '67f6c4eed5e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('suppliers') as batch_op:
        batch_op.alter_column(
            'okpo',
            new_column_name='edrpou',
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('suppliers') as batch_op:
        batch_op.alter_column(
            'edrpou',
            new_column_name='okpo',
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
            existing_nullable=False,
        )
