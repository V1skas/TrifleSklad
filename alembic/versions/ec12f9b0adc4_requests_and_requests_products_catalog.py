"""requests and requests_products_catalog

Revision ID: ec12f9b0adc4
Revises: f73dd7a21736
Create Date: 2026-06-06 21:21:02.469329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'ec12f9b0adc4'
down_revision: Union[str, None] = 'f73dd7a21736'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_table('requests'):
        op.create_table('requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=False),
        sa.Column('id_author', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_responsible', sa.Integer(), nullable=True),
        sa.Column('id_destination_storage', sa.Integer(), nullable=True),
        sa.Column('date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('comment', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('id_movement', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_author'], ['users.login'], ),
        sa.ForeignKeyConstraint(['id_destination_storage'], ['storages.id'], ),
        sa.ForeignKeyConstraint(['id_movement'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['id_responsible'], ['workers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('requests_products_catalog'):
        op.create_table('requests_products_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_request', sa.Integer(), nullable=False),
        sa.Column('id_product_catalog', sa.Integer(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_product_catalog'], ['products_catalog.id'], ),
        sa.ForeignKeyConstraint(['id_request'], ['requests.id'], ),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_table('requests_products_catalog'):
        op.drop_table('requests_products_catalog')
    if _has_table('requests'):
        op.drop_table('requests')
