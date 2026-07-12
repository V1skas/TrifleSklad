"""TS-39 client_issues

Revision ID: b1e2c4a9f6d3
Revises: 024ed6b9012c
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'b1e2c4a9f6d3'
down_revision: Union[str, None] = '024ed6b9012c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('client_issues',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_recipient', sa.Integer(), nullable=False),
    sa.Column('contract_number', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('installation_address', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['movements.id'], ),
    sa.ForeignKeyConstraint(['id_recipient'], ['workers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('client_issues')
