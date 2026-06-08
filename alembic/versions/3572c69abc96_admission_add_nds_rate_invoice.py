"""admissions: add id_nds_rate, invoice_number

Revision ID: 3572c69abc96
Revises: 92c6928185b1
Create Date: 2026-05-31 00:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = '3572c69abc96'
down_revision: Union[str, None] = '92c6928185b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_fk(table: str, name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return name in {fk["name"] for fk in insp.get_foreign_keys(table)}


def upgrade() -> None:
    with op.batch_alter_table('admissions') as batch_op:
        if not _has_column('admissions', 'id_nds_rate'):
            batch_op.add_column(
                sa.Column('id_nds_rate', sa.Integer(), nullable=True)
            )
        if not _has_column('admissions', 'invoice_number'):
            batch_op.add_column(
                sa.Column('invoice_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
            )
        if not _has_fk('admissions', 'fk_admissions_nds_rates'):
            batch_op.create_foreign_key(
                'fk_admissions_nds_rates',
                'nds_rates',
                ['id_nds_rate'],
                ['id'],
            )


def downgrade() -> None:
    with op.batch_alter_table('admissions') as batch_op:
        if _has_fk('admissions', 'fk_admissions_nds_rates'):
            batch_op.drop_constraint('fk_admissions_nds_rates', type_='foreignkey')
        if _has_column('admissions', 'invoice_number'):
            batch_op.drop_column('invoice_number')
        if _has_column('admissions', 'id_nds_rate'):
            batch_op.drop_column('id_nds_rate')
