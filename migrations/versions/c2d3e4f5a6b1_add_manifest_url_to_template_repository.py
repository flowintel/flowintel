"""add manifest_url to template_repository

Revision ID: c2d3e4f5a6b1
Revises: b1c2d3e4f5a6
Create Date: 2026-03-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'c2d3e4f5a6b1'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = [c['name'] for c in inspector.get_columns('template__repository')]

    if 'manifest_url' not in existing_columns:
        with op.batch_alter_table('template__repository') as batch_op:
            batch_op.add_column(sa.Column('manifest_url', sa.String(length=512), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = [c['name'] for c in inspector.get_columns('template__repository')]

    if 'manifest_url' in existing_columns:
        with op.batch_alter_table('template__repository') as batch_op:
            batch_op.drop_column('manifest_url')
