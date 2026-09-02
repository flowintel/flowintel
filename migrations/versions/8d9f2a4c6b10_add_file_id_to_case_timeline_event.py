"""Add file_id to case timeline event

Revision ID: 8d9f2a4c6b10
Revises: 51c89f0d2a4b
Create Date: 2026-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '8d9f2a4c6b10'
down_revision = '51c89f0d2a4b'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('case__timeline__event')]

    if 'file_id' not in columns:
        with op.batch_alter_table('case__timeline__event', schema=None) as batch_op:
            batch_op.add_column(sa.Column('file_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f('ix_case__timeline__event_file_id'), ['file_id'], unique=False)
            batch_op.create_foreign_key(
                batch_op.f('fk_case__timeline__event_file_id_file'),
                'file',
                ['file_id'],
                ['id'],
                ondelete='CASCADE'
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('case__timeline__event')]

    if 'file_id' in columns:
        with op.batch_alter_table('case__timeline__event', schema=None) as batch_op:
            batch_op.drop_constraint(batch_op.f('fk_case__timeline__event_file_id_file'), type_='foreignkey')
            batch_op.drop_index(batch_op.f('ix_case__timeline__event_file_id'))
            batch_op.drop_column('file_id')
