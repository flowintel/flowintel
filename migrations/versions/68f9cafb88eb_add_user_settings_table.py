"""add user settings table

Revision ID: 68f9cafb88eb
Revises: 4f62a1b8c9d0
Create Date: 2026-09-25 11:59:39.885618

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '68f9cafb88eb'
down_revision = '4f62a1b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    # Check what exists before making changes
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'user_settings' not in inspector.get_table_names():
        op.create_table('user_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(length=16), server_default='auto', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    else:
        print("Table 'user_settings' already exists")

    indexes = [idx['name'] for idx in sa.inspect(bind).get_indexes('user_settings')]
    if 'ix_user_settings_user_id' not in indexes:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_user_settings_user_id'), ['user_id'], unique=True)
    else:
        print("Index 'ix_user_settings_user_id' already exists")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'user_settings' not in inspector.get_table_names():
        print("Table 'user_settings' does not exist")
        return

    indexes = [idx['name'] for idx in inspector.get_indexes('user_settings')]
    if 'ix_user_settings_user_id' in indexes:
        with op.batch_alter_table('user_settings', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_user_settings_user_id'))

    op.drop_table('user_settings')
