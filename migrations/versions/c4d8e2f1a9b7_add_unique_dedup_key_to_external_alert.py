"""Add a unique constraint on external alert de-duplication key

Revision ID: c4d8e2f1a9b7
Revises: ddcd67403ee0
Create Date: 2026-10-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d8e2f1a9b7'
down_revision = 'ddcd67403ee0'
branch_labels = None
depends_on = None


EXTERNAL_ALERT_TABLE = 'external_alert'
DEDUP_CONSTRAINT = 'uq_external_alert_connector_dedup_key'
DEDUP_COLUMNS = ['connector_instance_id', 'deduplication_key']


def _has_dedup_constraint(inspector):
    names = {uc['name'] for uc in inspector.get_unique_constraints(EXTERNAL_ALERT_TABLE)}
    names.update(idx['name'] for idx in inspector.get_indexes(EXTERNAL_ALERT_TABLE) if idx.get('unique'))
    return DEDUP_CONSTRAINT in names


def _clear_duplicate_dedup_keys():
    # Concurrent ingests could store several alerts under the same
    # (connector_instance_id, deduplication_key). Keep the oldest alert as the
    # de-duplication target and clear the key on the others, so the constraint
    # can be created without deleting any alert.
    op.execute(
        sa.text(
            f"""
            UPDATE {EXTERNAL_ALERT_TABLE}
            SET deduplication_key = NULL
            WHERE connector_instance_id IS NOT NULL
              AND deduplication_key IS NOT NULL
              AND id NOT IN (
                  SELECT keep_id FROM (
                      SELECT MIN(id) AS keep_id
                      FROM {EXTERNAL_ALERT_TABLE}
                      WHERE connector_instance_id IS NOT NULL
                        AND deduplication_key IS NOT NULL
                      GROUP BY connector_instance_id, deduplication_key
                  ) AS keep_rows
              )
            """
        )
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if EXTERNAL_ALERT_TABLE not in inspector.get_table_names() or _has_dedup_constraint(inspector):
        return

    _clear_duplicate_dedup_keys()

    with op.batch_alter_table(EXTERNAL_ALERT_TABLE, schema=None) as batch_op:
        batch_op.create_unique_constraint(DEDUP_CONSTRAINT, DEDUP_COLUMNS)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if EXTERNAL_ALERT_TABLE not in inspector.get_table_names() or not _has_dedup_constraint(inspector):
        return

    with op.batch_alter_table(EXTERNAL_ALERT_TABLE, schema=None) as batch_op:
        batch_op.drop_constraint(DEDUP_CONSTRAINT, type_='unique')
