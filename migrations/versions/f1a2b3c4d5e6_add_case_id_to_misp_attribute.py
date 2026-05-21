"""Add case_id to misp_attribute for standalone attributes

Revision ID: f1a2b3c4d5e6
Revises: 056a43a96b07
Create Date: 2026-05-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '056a43a96b07'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('misp__attribute')]
    if 'case_id' not in columns:
        with op.batch_alter_table('misp__attribute', schema=None) as batch_op:
            batch_op.add_column(sa.Column('case_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f('ix_misp__attribute_case_id'), ['case_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('misp__attribute')]
    if 'case_id' in columns:
        with op.batch_alter_table('misp__attribute', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_misp__attribute_case_id'))
            batch_op.drop_column('case_id')
