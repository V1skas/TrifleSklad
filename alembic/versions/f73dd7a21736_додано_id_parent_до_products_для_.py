"""Додано id_parent до products для подільного ТМЦ

Revision ID: f73dd7a21736
Revises: 3572c69abc96
Create Date: 2026-06-05 23:54:29.331412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'f73dd7a21736'
down_revision: Union[str, None] = '3572c69abc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_fk(table: str, name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return name in {fk["name"] for fk in insp.get_foreign_keys(table)}


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        if not _has_column('products', 'id_parent'):
            batch_op.add_column(sa.Column('id_parent', sa.Integer(), nullable=True))
        if not _has_fk('products', 'fk_products_id_parent_products'):
            batch_op.create_foreign_key(
                'fk_products_id_parent_products', 'products', ['id_parent'], ['id']
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        if _has_fk('products', 'fk_products_id_parent_products'):
            batch_op.drop_constraint('fk_products_id_parent_products', type_='foreignkey')
        if _has_column('products', 'id_parent'):
            batch_op.drop_column('id_parent')
