"""add auth_provider to user

Revision ID: 598df1c175e3
Revises: 26c7e5d76677
Create Date: 2026-02-20 21:54:31.776484

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '598df1c175e3'
down_revision = '26c7e5d76677'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('auth_provider', sa.String(length=32), server_default='local', nullable=False))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('auth_provider')
