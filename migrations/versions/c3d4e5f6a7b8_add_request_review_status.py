"""Add Request Review status and order column to Status table

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('status')]

    # Add order column to status table
    if 'order' not in columns:
        op.add_column('status', sa.Column('order', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_status_order'), 'status', ['order'], unique=False)
    else:
        print("Column order already exists in status")

    # Insert "Request Review" status if it doesn't exist
    result = conn.execute(sa.text("SELECT 1 FROM status WHERE name = 'Request Review'"))
    if not result.fetchone():
        op.execute("INSERT INTO status (name, bootstrap_style, \"order\") VALUES ('Request Review', 'warning', 5)")
    else:
        print("Status 'Request Review' already exists")

    # Set display order for all existing statuses
    # Desired order: Created(1), Requested(2), Approved(3), Ongoing(4), Request Review(5), Finished(6), Rejected(7), Recurring(8), Unavailable(9)
    op.execute("UPDATE status SET \"order\" = 1 WHERE name = 'Created'")
    op.execute("UPDATE status SET \"order\" = 2 WHERE name = 'Requested'")
    op.execute("UPDATE status SET \"order\" = 3 WHERE name = 'Approved'")
    op.execute("UPDATE status SET \"order\" = 4 WHERE name = 'Ongoing'")
    # Request Review already set to 5 above
    op.execute("UPDATE status SET \"order\" = 6 WHERE name = 'Finished'")
    op.execute("UPDATE status SET \"order\" = 7 WHERE name = 'Rejected'")
    op.execute("UPDATE status SET \"order\" = 8 WHERE name = 'Recurring'")
    op.execute("UPDATE status SET \"order\" = 9 WHERE name = 'Unavailable'")


def downgrade():
    # Remove "Request Review" status
    op.execute("DELETE FROM status WHERE name = 'Request Review'")

    # Drop order column
    op.drop_index(op.f('ix_status_order'), table_name='status')
    op.drop_column('status', 'order')
