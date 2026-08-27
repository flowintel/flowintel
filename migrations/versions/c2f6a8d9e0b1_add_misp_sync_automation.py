"""Add MISP sync automation tables

Revision ID: c2f6a8d9e0b1
Revises: 0f3c7b8a1d22
Create Date: 2026-07-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c2f6a8d9e0b1'
down_revision = '0f3c7b8a1d22'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'case__misp__sync__schedule' not in existing_tables:
        op.create_table(
            'case__misp__sync__schedule',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('case_id', sa.Integer(), nullable=True),
            sa.Column('case_connector_instance_id', sa.Integer(), nullable=True),
            sa.Column('direction', sa.String(length=10), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('interval', sa.String(length=20), nullable=False),
            sa.Column('on_change', sa.Boolean(), nullable=False),
            sa.Column('module_name', sa.String(length=128), nullable=True),
            sa.Column('payload', sa.JSON(), nullable=True),
            sa.Column('conflict_strategy', sa.String(length=30), nullable=False),
            sa.Column('last_run_at', sa.DateTime(), nullable=True),
            sa.Column('next_run_at', sa.DateTime(), nullable=True),
            sa.Column('last_seen_case_modif', sa.DateTime(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.Column('updated_by_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('case_connector_instance_id', 'direction', name='uq_case_misp_sync_schedule_connector_direction')
        )
        with op.batch_alter_table('case__misp__sync__schedule', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_case__misp__sync__schedule_case_connector_instance_id'), ['case_connector_instance_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__schedule_case_id'), ['case_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__schedule_created_by_id'), ['created_by_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__schedule_direction'), ['direction'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__schedule_next_run_at'), ['next_run_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__schedule_updated_by_id'), ['updated_by_id'], unique=False)

    if 'case__misp__sync__conflict' not in existing_tables:
        op.create_table(
            'case__misp__sync__conflict',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('case_id', sa.Integer(), nullable=True),
            sa.Column('case_connector_instance_id', sa.Integer(), nullable=True),
            sa.Column('direction', sa.String(length=10), nullable=True),
            sa.Column('item_type', sa.String(length=30), nullable=True),
            sa.Column('local_ref', sa.String(), nullable=True),
            sa.Column('remote_ref', sa.String(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('base_snapshot', sa.JSON(), nullable=True),
            sa.Column('local_snapshot', sa.JSON(), nullable=True),
            sa.Column('remote_snapshot', sa.JSON(), nullable=True),
            sa.Column('resolution', sa.String(length=30), nullable=True),
            sa.Column('resolution_payload', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.Column('resolved_by_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('case__misp__sync__conflict', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_case_connector_instance_id'), ['case_connector_instance_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_case_id'), ['case_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_direction'), ['direction'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_item_type'), ['item_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_resolved_by_id'), ['resolved_by_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__sync__conflict_status'), ['status'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'case__misp__sync__conflict' in existing_tables:
        with op.batch_alter_table('case__misp__sync__conflict', schema=None) as batch_op:
            for index_name in [
                'ix_case__misp__sync__conflict_status',
                'ix_case__misp__sync__conflict_resolved_by_id',
                'ix_case__misp__sync__conflict_item_type',
                'ix_case__misp__sync__conflict_direction',
                'ix_case__misp__sync__conflict_created_at',
                'ix_case__misp__sync__conflict_case_id',
                'ix_case__misp__sync__conflict_case_connector_instance_id'
            ]:
                batch_op.drop_index(index_name)
        op.drop_table('case__misp__sync__conflict')

    if 'case__misp__sync__schedule' in existing_tables:
        with op.batch_alter_table('case__misp__sync__schedule', schema=None) as batch_op:
            for index_name in [
                'ix_case__misp__sync__schedule_updated_by_id',
                'ix_case__misp__sync__schedule_next_run_at',
                'ix_case__misp__sync__schedule_direction',
                'ix_case__misp__sync__schedule_created_by_id',
                'ix_case__misp__sync__schedule_case_id',
                'ix_case__misp__sync__schedule_case_connector_instance_id'
            ]:
                batch_op.drop_index(index_name)
        op.drop_table('case__misp__sync__schedule')
