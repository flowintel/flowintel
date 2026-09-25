"""add font to user settings

Revision ID: ddcd67403ee0
Revises: 68f9cafb88eb
Create Date: 2026-09-25 12:58:40.218125

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ddcd67403ee0'
down_revision = '68f9cafb88eb'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('user_settings')]

    if 'font' not in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('font', sa.String(length=16), server_default='rubik', nullable=False))
    else:
        print("Column 'font' already exists in 'user_settings'")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('user_settings')]

    if 'font' in columns:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.drop_column('font')
    else:
        print("Column 'font' does not exist in 'user_settings'")
