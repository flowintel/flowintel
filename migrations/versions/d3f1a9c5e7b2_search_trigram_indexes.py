"""trigram indexes for the top bar search (PostgreSQL only)

Revision ID: d3f1a9c5e7b2
Revises: b7d2c4e6f8a1
Create Date: 2026-11-19 18:00:00.000000

The global search filters with ILIKE '%text%', which a B-tree index cannot serve. On
PostgreSQL, pg_trgm GIN indexes make those filters use an index, so the search stays fast
with millions of cases / tasks / notes / attributes. Other databases are left as they are
(the search bounds every query and gives up a kind after a time budget instead).
"""
from alembic import op
import sqlalchemy as sa


revision = 'd3f1a9c5e7b2'
down_revision = 'b7d2c4e6f8a1'
branch_labels = None
depends_on = None

# (index name, table, column)
INDEXES = (
    ("ix_trgm_case_title", "case", "title"),
    ("ix_trgm_case_ticket_id", "case", "ticket_id"),
    ("ix_trgm_task_title", "task", "title"),
    ("ix_trgm_note_note", "note", "note"),
    ("ix_trgm_misp_attribute_value", "misp__attribute", "value"),
    ("ix_trgm_tags_name", "tags", "name"),
    ("ix_trgm_custom_tags_name", "custom__tags", "name"),
    ("ix_trgm_cluster_name", "cluster", "name"),
    ("ix_trgm_cluster_tag", "cluster", "tag"),
)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    except Exception as e:  # no right to create extensions: the search still works, only slower
        print(f"pg_trgm not available, search indexes skipped: {e}")
        return
    tables = set(sa.inspect(bind).get_table_names())
    for name, table, column in INDEXES:
        if table in tables:
            op.execute(f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" USING gin ({column} gin_trgm_ops)')


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, _table, _column in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
