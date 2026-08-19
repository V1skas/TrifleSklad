"""TS-43 audit log

Revision ID: e464f7703e20
Revises: a3f7d21c9e04
Create Date: 2026-07-19 21:52:56.569033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'e464f7703e20'
down_revision: Union[str, None] = 'a3f7d21c9e04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_user', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('action', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('table_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('record_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('changes', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['id_user'], ['users.login'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_log_record_id'), ['record_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_log_table_name'), ['table_name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_log_table_name'))
        batch_op.drop_index(batch_op.f('ix_audit_log_record_id'))

    op.drop_table('audit_log')
