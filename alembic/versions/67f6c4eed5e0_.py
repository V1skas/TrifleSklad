"""empty message

Revision ID: 67f6c4eed5e0
Revises:
Create Date: 2026-02-22 21:05:29.691514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '67f6c4eed5e0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_table('actions'):
        op.create_table('actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
        )
    if not _has_table('owners'):
        op.create_table('owners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('payment_types'):
        op.create_table('payment_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('title')
        )
    if not _has_table('product_categories'):
        op.create_table('product_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('roles'):
        op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('suppliers'):
        op.create_table('suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('contact_person', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('contact_phone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('okpo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('workers'):
        op.create_table('workers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fio', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('phone_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('position', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('products_catalog'):
        op.create_table('products_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('id_category', sa.Integer(), nullable=True),
        sa.Column('unit', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('divisible', sa.Boolean(), nullable=False),
        sa.Column('uniq', sa.Boolean(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('count', sa.Float(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_category'], ['product_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('roles_actions'):
        op.create_table('roles_actions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('action_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['action_id'], ['actions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('role_id', 'action_id')
        )
    if not _has_table('storages'):
        op.create_table('storages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_responsible', sa.Integer(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_responsible'], ['workers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('users'):
        op.create_table('users',
        sa.Column('login', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_worker', sa.Integer(), nullable=True),
        sa.Column('salt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_worker'], ['workers.id'], ),
        sa.PrimaryKeyConstraint('login')
        )
    if not _has_table('auth_tokens'):
        op.create_table('auth_tokens',
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_user', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['id_user'], ['users.login'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
        )
    if not _has_table('movements'):
        op.create_table('movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=False),
        sa.Column('id_user', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_incoming_storage', sa.Integer(), nullable=True),
        sa.Column('id_destination_storage', sa.Integer(), nullable=True),
        sa.Column('id_incoming_owner', sa.Integer(), nullable=True),
        sa.Column('id_destination_owner', sa.Integer(), nullable=True),
        sa.Column('date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('comment', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['id_destination_owner'], ['owners.id'], ),
        sa.ForeignKeyConstraint(['id_destination_storage'], ['storages.id'], ),
        sa.ForeignKeyConstraint(['id_incoming_owner'], ['owners.id'], ),
        sa.ForeignKeyConstraint(['id_incoming_storage'], ['storages.id'], ),
        sa.ForeignKeyConstraint(['id_user'], ['users.login'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('products'):
        op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('serial_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('id_product_catalog', sa.Integer(), nullable=False),
        sa.Column('id_storage', sa.Integer(), nullable=False),
        sa.Column('id_owner', sa.Integer(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_owner'], ['owners.id'], ),
        sa.ForeignKeyConstraint(['id_product_catalog'], ['products_catalog.id'], ),
        sa.ForeignKeyConstraint(['id_storage'], ['storages.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('users_actions'):
        op.create_table('users_actions',
        sa.Column('id_user', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_action', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_action'], ['actions.id'], ),
        sa.ForeignKeyConstraint(['id_user'], ['users.login'], ),
        sa.PrimaryKeyConstraint('id_user', 'id_action')
        )
    if not _has_table('users_roles'):
        op.create_table('users_roles',
        sa.Column('id_user', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id_role', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_role'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['id_user'], ['users.login'], ),
        sa.PrimaryKeyConstraint('id_user', 'id_role')
        )
    if not _has_table('admissions'):
        op.create_table('admissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_payment_type', sa.Integer(), nullable=False),
        sa.Column('id_supplier', sa.Integer(), nullable=False),
        sa.Column('flag_nds', sa.Boolean(), nullable=False),
        sa.Column('dollar_rate', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['id_payment_type'], ['payment_types.id'], ),
        sa.ForeignKeyConstraint(['id_supplier'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('issues'):
        op.create_table('issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_recipient', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['id_recipient'], ['workers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('movements_products_catalog'):
        op.create_table('movements_products_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_movement', sa.Integer(), nullable=False),
        sa.Column('id_product_catalog', sa.Integer(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['id_movement'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['id_product_catalog'], ['products_catalog.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('sales'):
        op.create_table('sales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_responsible', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['id_responsible'], ['workers.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_table('movements_products'):
        op.create_table('movements_products',
        sa.Column('id_movement_product', sa.Integer(), nullable=False),
        sa.Column('id_product', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_movement_product'], ['movements_products_catalog.id'], ),
        sa.ForeignKeyConstraint(['id_product'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id_movement_product', 'id_product')
        )


def downgrade() -> None:
    """Downgrade schema."""
    for _table in (
        'movements_products',
        'sales',
        'movements_products_catalog',
        'issues',
        'admissions',
        'users_roles',
        'users_actions',
        'products',
        'movements',
        'auth_tokens',
        'users',
        'storages',
        'roles_actions',
        'products_catalog',
        'workers',
        'suppliers',
        'roles',
        'product_categories',
        'payment_types',
        'owners',
        'actions',
    ):
        if _has_table(_table):
            op.drop_table(_table)
