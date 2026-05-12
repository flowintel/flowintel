"""Add Task_Misp_Object link table

Revision ID: e1a2b3c4d5f6
Revises: c45dc323e50c
Create Date: 2026-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5f6'
down_revision = 'c45dc323e50c'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'task__misp__object' not in inspector.get_table_names():
        op.create_table(
            'task__misp__object',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('task_id', sa.Integer(), nullable=True),
            sa.Column('misp_object_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['misp_object_id'], ['case__misp__object.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('task__misp__object', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_task__misp__object_task_id'), ['task_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_task__misp__object_misp_object_id'), ['misp_object_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'task__misp__object' in inspector.get_table_names():
        with op.batch_alter_table('task__misp__object', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_task__misp__object_misp_object_id'))
            batch_op.drop_index(batch_op.f('ix_task__misp__object_task_id'))
        op.drop_table('task__misp__object')
