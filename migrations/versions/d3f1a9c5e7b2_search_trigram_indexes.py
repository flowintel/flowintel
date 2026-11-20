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
    installed = bind.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).first()
    if not installed:
        available = bind.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm'")).first()
        if not available:
            print("pg_trgm not available on this server, search indexes skipped")
            return
        # in a savepoint: a refused CREATE EXTENSION (no right) must not abort the whole migration transaction
        try:
            with bind.begin_nested():
                bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        except Exception as e:  # the search still works, only slower
            print(f"pg_trgm could not be created, search indexes skipped: {e}")
            return
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for name, table, column in INDEXES:
        if table not in tables:
            print(f"Table '{table}' does not exist, index '{name}' skipped")
            continue
        if column not in [c["name"] for c in inspector.get_columns(table)]:
            print(f"Column '{table}.{column}' does not exist, index '{name}' skipped")
            continue
        if name in [i["name"] for i in inspector.get_indexes(table)]:
            print(f"Index '{name}' already exists")
            continue
        op.execute(f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" USING gin ({column} gin_trgm_ops)')


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, _table, _column in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
