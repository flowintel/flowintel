"""add case_view and tag_view to user settings

Revision ID: b7d2c4e6f8a1
Revises: c3e5a7b9d1f2
Create Date: 2026-11-19 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d2c4e6f8a1'
down_revision = 'c3e5a7b9d1f2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    columns = [col['name'] for col in sa.inspect(conn).get_columns('user_settings')]

    if 'case_view' not in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('case_view', sa.String(length=16), server_default='cards', nullable=False))
    else:
        print("Column 'case_view' already exists in 'user_settings'")

    if 'tag_view' not in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('tag_view', sa.String(length=16), server_default='compact', nullable=False))
    else:
        print("Column 'tag_view' already exists in 'user_settings'")


def downgrade():
    conn = op.get_bind()
    columns = [col['name'] for col in sa.inspect(conn).get_columns('user_settings')]

    if 'tag_view' in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.drop_column('tag_view')

    if 'case_view' in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.drop_column('case_view')
    else:
        print("Column 'case_view' does not exist in 'user_settings'")
