"""replace manifest_url with local_path in template_repository

Revision ID: g6b7c8d9e0f1
Revises: f5a6b7c8d9e4
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'g6b7c8d9e0f1'
down_revision = 'f5a6b7c8d9e4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('template__repository') as batch_op:
        batch_op.add_column(sa.Column('local_path', sa.String(512), nullable=True))
        batch_op.drop_column('manifest_url')


def downgrade():
    with op.batch_alter_table('template__repository') as batch_op:
        batch_op.add_column(sa.Column('manifest_url', sa.String(512), nullable=True))
        batch_op.drop_column('local_path')
