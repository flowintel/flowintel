"""add sticky_header to user settings

Revision ID: e4a2b6c8d0f1
Revises: d3f1a9c5e7b2
Create Date: 2026-11-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4a2b6c8d0f1'
down_revision = 'd3f1a9c5e7b2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if not sa.inspect(conn).has_table('user_settings'):
        print("Table 'user_settings' does not exist, 'sticky_header' skipped")
        return
    columns = [col['name'] for col in sa.inspect(conn).get_columns('user_settings')]
    if 'sticky_header' not in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('sticky_header', sa.String(length=16), server_default='fixed', nullable=False))
    else:
        print("Column 'sticky_header' already exists in 'user_settings'")


def downgrade():
    conn = op.get_bind()
    if not sa.inspect(conn).has_table('user_settings'):
        return
    columns = [col['name'] for col in sa.inspect(conn).get_columns('user_settings')]
    if 'sticky_header' in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.drop_column('sticky_header')
    else:
        print("Column 'sticky_header' does not exist in 'user_settings'")
