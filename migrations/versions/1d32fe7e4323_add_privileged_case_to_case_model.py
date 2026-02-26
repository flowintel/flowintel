"""Add privileged_case to Case model

Revision ID: 1d32fe7e4323
Revises: 233237ff2760
Create Date: 2026-02-02 12:17:52.850335

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1d32fe7e4323'
down_revision = '233237ff2760'
branch_labels = None
depends_on = None


def upgrade():
    # Add privileged_case column to case table
    with op.batch_alter_table('case', schema=None) as batch_op:
        # Check if column exists before adding
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('case')]
        
        if 'privileged_case' not in columns:
            batch_op.add_column(sa.Column('privileged_case', sa.Boolean(), nullable=True))
    
    # Set default value for existing rows (PostgreSQL and SQLite compatible)
    op.execute('UPDATE "case" SET privileged_case = FALSE WHERE privileged_case IS NULL')


def downgrade():
    # Remove privileged_case column from case table
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.drop_column('privileged_case')
