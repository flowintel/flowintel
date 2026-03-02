"""add version to template_repository

Revision ID: d3e4f5a6b7c2
Revises: c2d3e4f5a6b1
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'd3e4f5a6b7c2'
down_revision = 'c2d3e4f5a6b1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('template__repository', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('template__repository', schema=None) as batch_op:
        batch_op.drop_column('version')
