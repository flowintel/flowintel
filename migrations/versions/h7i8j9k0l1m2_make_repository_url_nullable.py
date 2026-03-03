"""make template_repository.url nullable

Revision ID: h7i8j9k0l1m2
Revises: g6b7c8d9e0f1
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'h7i8j9k0l1m2'
down_revision = 'g6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('template__repository') as batch_op:
        batch_op.alter_column('url', existing_type=sa.String(512), nullable=True)


def downgrade():
    with op.batch_alter_table('template__repository') as batch_op:
        batch_op.alter_column('url', existing_type=sa.String(512), nullable=False)
