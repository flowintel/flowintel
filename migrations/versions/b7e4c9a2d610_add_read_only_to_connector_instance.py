"""Add read-only mode to connector instances.

Revision ID: b7e4c9a2d610
Revises: c4d8e2f1a9b7
"""

from alembic import op
import sqlalchemy as sa


revision = 'b7e4c9a2d610'
down_revision = 'c4d8e2f1a9b7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('connector__instance') as batch_op:
        batch_op.add_column(sa.Column('read_only', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('connector__instance') as batch_op:
        batch_op.drop_column('read_only')
