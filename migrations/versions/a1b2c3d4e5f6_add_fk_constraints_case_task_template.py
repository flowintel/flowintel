"""Add FK constraints to Case_Task_Template

Revision ID: a1b2c3d4e5f6
Revises: f8c4a065648d
Create Date: 2026-04-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f8c4a065648d'
branch_labels = None
depends_on = None


def upgrade():
    # Clean up orphaned rows so the new FK constraints can be applied.
    connection = op.get_bind()
    connection.execute(sa.text(
        "DELETE FROM case__task__template "
        "WHERE case_id NOT IN (SELECT id FROM case__template)"
    ))
    connection.execute(sa.text(
        "DELETE FROM case__task__template "
        "WHERE task_id NOT IN (SELECT id FROM task__template)"
    ))

    with op.batch_alter_table('case__task__template', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_case_task_template_case_id',
            'case__template', ['case_id'], ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_case_task_template_task_id',
            'task__template', ['task_id'], ['id'],
            ondelete='CASCADE'
        )


def downgrade():
    with op.batch_alter_table('case__task__template', schema=None) as batch_op:
        batch_op.drop_constraint('fk_case_task_template_task_id', type_='foreignkey')
        batch_op.drop_constraint('fk_case_task_template_case_id', type_='foreignkey')
