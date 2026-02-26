"""Add audit_viewer to Role model

Revision ID: 26c7e5d76677
Revises: 8e8ade3bbb4a
Create Date: 2026-02-13 22:49:33.477122

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26c7e5d76677'
down_revision = '8e8ade3bbb4a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    role_columns = [col['name'] for col in inspector.get_columns('role')]
    
    with op.batch_alter_table('role', schema=None) as batch_op:
        if 'audit_viewer' not in role_columns:
            batch_op.add_column(sa.Column('audit_viewer', sa.Boolean(), nullable=True, default=False))


def downgrade():
    with op.batch_alter_table('role', schema=None) as batch_op:
        batch_op.drop_column('audit_viewer')
