"""add parent_case_uuid and parent_case_title to template_repository_entry

Revision ID: f5a6b7c8d9e4
Revises: e4f5a6b7c8d3
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5a6b7c8d9e4'
down_revision = 'e4f5a6b7c8d3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('template__repository_entry') as batch_op:
        batch_op.add_column(sa.Column('parent_case_uuid', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('parent_case_title', sa.String(256), nullable=True))
        batch_op.create_index('ix_template__repository_entry_parent_case_uuid', ['parent_case_uuid'])


def downgrade():
    with op.batch_alter_table('template__repository_entry') as batch_op:
        batch_op.drop_index('ix_template__repository_entry_parent_case_uuid')
        batch_op.drop_column('parent_case_title')
        batch_op.drop_column('parent_case_uuid')
