"""TS-40 id_parent for product_categories

Revision ID: 024ed6b9012c
Revises: 0a785a0eba78
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '024ed6b9012c'
down_revision: Union[str, None] = '0a785a0eba78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('product_categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id_parent', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_product_categories_id_parent_product_categories', 'product_categories', ['id_parent'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('product_categories', schema=None) as batch_op:
        batch_op.drop_constraint('fk_product_categories_id_parent_product_categories', type_='foreignkey')
        batch_op.drop_column('id_parent')
