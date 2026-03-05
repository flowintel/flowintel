"""add template_repository and template_repository_entry tables

Revision ID: b1c2d3e4f5a6
Revises: 5e8211f301aa
Create Date: 2026-02-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = '5e8211f301aa'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'template__repository' not in existing_tables:
        op.create_table(
            'template__repository',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('uuid', sa.String(length=36), nullable=True),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('url', sa.String(length=512), nullable=True),
            sa.Column('local_path', sa.String(length=512), nullable=True),
            sa.Column('version', sa.Integer(), nullable=True),
            sa.Column('creation_date', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('template__repository') as batch_op:
            batch_op.create_index('ix_template__repository_creation_date', ['creation_date'])
            batch_op.create_index('ix_template__repository_name', ['name'])
            batch_op.create_index('ix_template__repository_uuid', ['uuid'], unique=True)

    if 'template__repository_entry' not in existing_tables:
        op.create_table(
            'template__repository_entry',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('repository_id', sa.Integer(),
                      sa.ForeignKey('template__repository.id', ondelete='CASCADE'),
                      nullable=False),
            sa.Column('uuid', sa.String(length=36), nullable=True),
            sa.Column('title', sa.String(length=256), nullable=True),
            sa.Column('type', sa.String(length=8), nullable=True),
            sa.Column('version', sa.Integer(), nullable=True),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('download_url', sa.String(length=512), nullable=True),
            sa.Column('remote_sha', sa.String(length=64), nullable=True),
            sa.Column('parent_case_uuid', sa.String(length=36), nullable=True),
            sa.Column('parent_case_title', sa.String(length=256), nullable=True),
            sa.Column('last_synced', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('template__repository_entry') as batch_op:
            batch_op.create_index('ix_template__repository_entry_repository_id', ['repository_id'])
            batch_op.create_index('ix_template__repository_entry_uuid', ['uuid'])
            batch_op.create_index('ix_template__repository_entry_type', ['type'])
            batch_op.create_index('ix_template__repository_entry_parent_case_uuid', ['parent_case_uuid'])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'template__repository_entry' in existing_tables:
        with op.batch_alter_table('template__repository_entry') as batch_op:
            batch_op.drop_index('ix_template__repository_entry_parent_case_uuid')
            batch_op.drop_index('ix_template__repository_entry_type')
            batch_op.drop_index('ix_template__repository_entry_uuid')
            batch_op.drop_index('ix_template__repository_entry_repository_id')
        op.drop_table('template__repository_entry')

    if 'template__repository' in existing_tables:
        with op.batch_alter_table('template__repository') as batch_op:
            batch_op.drop_index('ix_template__repository_uuid')
            batch_op.drop_index('ix_template__repository_name')
            batch_op.drop_index('ix_template__repository_creation_date')
        op.drop_table('template__repository')
