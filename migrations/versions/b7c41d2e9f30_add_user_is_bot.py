"""Add an explicit Matrix relay marker without trusting editable profile fields.

Existing accounts remain unmarked. Operators register the known bot by database
ID using bin/register_matrix_bot.py after applying this migration.

Revision ID: b7c41d2e9f30
Revises: b7e4c9a2d610
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c41d2e9f30'
down_revision = 'b7e4c9a2d610'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('user')}
    if 'is_bot' not in columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_bot', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_bot')
