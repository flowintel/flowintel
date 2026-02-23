"""add auth_provider to user

Revision ID: 598df1c175e3
Revises: 697786a00ccd
Create Date: 2026-02-20 21:54:31.776484

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '598df1c175e3'
down_revision = '697786a00ccd'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('user')]

    with op.batch_alter_table('user', schema=None) as batch_op:
        if 'auth_provider' not in existing_columns:
            batch_op.add_column(sa.Column('auth_provider', sa.String(length=32), server_default='local', nullable=False))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('user')]

    with op.batch_alter_table('user', schema=None) as batch_op:
        if 'auth_provider' in existing_columns:
            batch_op.drop_column('auth_provider')
