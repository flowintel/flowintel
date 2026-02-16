"""Add task statuses Requested and Approved

Revision ID: 7d4459c0a46f
Revises: 1d32fe7e4323
Create Date: 2026-02-03 16:33:09.600833

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '7d4459c0a46f'
down_revision = '1d32fe7e4323'
branch_labels = None
depends_on = None


def upgrade():
    # Add Requested and Approved statuses if they don't exist
    # Note: Rejected status already exists in the database as ID 5
    bind = op.get_bind()
    
    # Check if Requested status exists
    result = bind.execute(text("SELECT COUNT(*) FROM status WHERE name = 'Requested'")).scalar()
    if result == 0:
        bind.execute(text("INSERT INTO status (name, bootstrap_style) VALUES ('Requested', 'warning')"))
    
    # Check if Approved status exists
    result = bind.execute(text("SELECT COUNT(*) FROM status WHERE name = 'Approved'")).scalar()
    if result == 0:
        bind.execute(text("INSERT INTO status (name, bootstrap_style) VALUES ('Approved', 'info')"))


def downgrade():
    # Remove Requested and Approved statuses
    bind = op.get_bind()
    bind.execute(text("DELETE FROM status WHERE name IN ('Requested', 'Approved')"))
