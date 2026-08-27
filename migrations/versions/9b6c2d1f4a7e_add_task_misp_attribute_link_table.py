"""Add Task_Misp_Attribute link table

Revision ID: 9b6c2d1f4a7e
Revises: f1a2b3c4d5e6
Create Date: 2026-05-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b6c2d1f4a7e'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()
    if 'task__misp__attribute' not in table_names:
        op.create_table(
            'task__misp__attribute',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('task_id', sa.Integer(), nullable=True),
            sa.Column('misp_attribute_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['misp_attribute_id'], ['misp__attribute.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    indexes = {idx['name'] for idx in inspector.get_indexes('task__misp__attribute')} if 'task__misp__attribute' in inspector.get_table_names() else set()
    with op.batch_alter_table('task__misp__attribute', schema=None) as batch_op:
        if 'ix_task__misp__attribute_task_id' not in indexes:
            batch_op.create_index(batch_op.f('ix_task__misp__attribute_task_id'), ['task_id'], unique=False)
        if 'ix_task__misp__attribute_misp_attribute_id' not in indexes:
            batch_op.create_index(batch_op.f('ix_task__misp__attribute_misp_attribute_id'), ['misp_attribute_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'task__misp__attribute' in inspector.get_table_names():
        indexes = {idx['name'] for idx in inspector.get_indexes('task__misp__attribute')}
        with op.batch_alter_table('task__misp__attribute', schema=None) as batch_op:
            if 'ix_task__misp__attribute_misp_attribute_id' in indexes:
                batch_op.drop_index(batch_op.f('ix_task__misp__attribute_misp_attribute_id'))
            if 'ix_task__misp__attribute_task_id' in indexes:
                batch_op.drop_index(batch_op.f('ix_task__misp__attribute_task_id'))
        op.drop_table('task__misp__attribute')
