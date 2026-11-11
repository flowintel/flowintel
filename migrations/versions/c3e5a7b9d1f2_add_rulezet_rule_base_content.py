"""Keep the version of a Rulezet rule as it was taken from Rulezet.

base_content is the rule's content the last time it was added or resynced from Rulezet.
Compared with the case's content and with Rulezet's current content, it tells whether
the rule was edited in Flowintel, changed on Rulezet, or both (a conflict on resync).

Revision ID: c3e5a7b9d1f2
Revises: b7c41d2e9f30
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3e5a7b9d1f2'
down_revision = 'b7c41d2e9f30'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('rulezet__rule')}
    if 'base_content' not in columns:
        with op.batch_alter_table('rulezet__rule', schema=None) as batch_op:
            batch_op.add_column(sa.Column('base_content', sa.Text(), nullable=True))
    # Rules added before: their content is the one taken from Rulezet
    op.execute("UPDATE rulezet__rule SET base_content = content WHERE base_content IS NULL")


def downgrade():
    with op.batch_alter_table('rulezet__rule', schema=None) as batch_op:
        batch_op.drop_column('base_content')
