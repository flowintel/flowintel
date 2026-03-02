"""add template_repository_entry table

Revision ID: e4f5a6b7c8d3
Revises: d3e4f5a6b7c2
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d3'
down_revision = 'd3e4f5a6b7c2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'template__repository_entry',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('repository_id', sa.Integer(),
                  sa.ForeignKey('template__repository.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('uuid', sa.String(36), index=True),
        sa.Column('title', sa.String(256)),
        sa.Column('type', sa.String(8), index=True),
        sa.Column('version', sa.Integer()),
        sa.Column('description', sa.String()),
        sa.Column('download_url', sa.String(512)),
        sa.Column('remote_sha', sa.String(64)),
        sa.Column('last_synced', sa.DateTime()),
    )


def downgrade():
    op.drop_table('template__repository_entry')
