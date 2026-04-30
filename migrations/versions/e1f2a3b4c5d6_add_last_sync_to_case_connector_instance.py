"""Add last_sync to Case_Connector_Instance

Revision ID: e1f2a3b4c5d6
Revises: d27a4e1b9c83
Create Date: 2026-04-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd27a4e1b9c83'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('case__connector__instance')]
    if 'last_sync' not in columns:
        with op.batch_alter_table('case__connector__instance', schema=None) as batch_op:
            batch_op.add_column(sa.Column('last_sync', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('case__connector__instance')]
    if 'last_sync' in columns:
        with op.batch_alter_table('case__connector__instance', schema=None) as batch_op:
            batch_op.drop_column('last_sync')
