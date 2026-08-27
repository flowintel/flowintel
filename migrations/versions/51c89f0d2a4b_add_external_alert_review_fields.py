"""Add external alert table

Revision ID: 51c89f0d2a4b
Revises: 6e947c30e21c
Create Date: 2026-08-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '51c89f0d2a4b'
down_revision = '6e947c30e21c'
branch_labels = None
depends_on = None


EXTERNAL_ALERT_TABLE = 'external_alert'
EXTERNAL_ALERT_ACTION_TABLE = 'external_alert_action'

EXTERNAL_ALERT_COLUMNS = [
    'id',
    'uuid',
    'case_id',
    'message',
    'status',
    'creation_date',
    'is_read',
    'title',
    'description',
    'severity',
    'confidence',
    'category',
    'tlp',
    'source',
    'source_ref',
    'source_url',
    'connector_instance_id',
    'owner_user_id',
    'owner_org_id',
    'review_status',
    'review_comment',
    'reviewed_by_id',
    'reviewed_at',
    'event_time',
    'last_seen',
    'occurrence_count',
    'deduplication_key',
    'raw_payload',
    'observables',
    'assets',
    'external_references',
    'mitre_attack',
    'recommended_actions',
    'tags',
]

ALERT_EXTERNAL_COLUMNS = [
    'uuid',
    'alert_type',
    'title',
    'description',
    'severity',
    'confidence',
    'category',
    'tlp',
    'source',
    'source_ref',
    'source_url',
    'connector_instance_id',
    'owner_user_id',
    'owner_org_id',
    'review_status',
    'review_comment',
    'reviewed_by_id',
    'reviewed_at',
    'event_time',
    'last_seen',
    'occurrence_count',
    'deduplication_key',
    'raw_payload',
    'observables',
    'assets',
    'external_references',
    'mitre_attack',
    'recommended_actions',
    'tags',
]

ALERT_EXTERNAL_INDEXES = [
    'ix_alert_deduplication_key',
    'ix_alert_last_seen',
    'ix_alert_event_time',
    'ix_alert_reviewed_at',
    'ix_alert_reviewed_by_id',
    'ix_alert_review_status',
    'ix_alert_owner_org_id',
    'ix_alert_owner_user_id',
    'ix_alert_connector_instance_id',
    'ix_alert_source_ref',
    'ix_alert_source',
    'ix_alert_tlp',
    'ix_alert_category',
    'ix_alert_severity',
    'ix_alert_title',
    'ix_alert_alert_type',
    'ix_alert_uuid',
]


def _column_names(inspector, table_name):
    return [col['name'] for col in inspector.get_columns(table_name)]


def _index_names(inspector, table_name):
    return [idx['name'] for idx in inspector.get_indexes(table_name)]


def _create_external_alert_table(inspector):
    if EXTERNAL_ALERT_TABLE in inspector.get_table_names():
        return

    op.create_table(
        EXTERNAL_ALERT_TABLE,
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('creation_date', sa.DateTime(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('category', sa.String(length=80), nullable=True),
        sa.Column('tlp', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=120), nullable=True),
        sa.Column('source_ref', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(8192), nullable=True),
        sa.Column('connector_instance_id', sa.Integer(), nullable=True),
        sa.Column('owner_user_id', sa.Integer(), nullable=True),
        sa.Column('owner_org_id', sa.Integer(), nullable=True),
        sa.Column('review_status', sa.String(length=30), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('event_time', sa.DateTime(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=True),
        sa.Column('deduplication_key', sa.String(length=255), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('observables', sa.JSON(), nullable=True),
        sa.Column('assets', sa.JSON(), nullable=True),
        sa.Column('external_references', sa.JSON(), nullable=True),
        sa.Column('mitre_attack', sa.JSON(), nullable=True),
        sa.Column('recommended_actions', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def _create_external_alert_indexes(inspector):
    existing_indexes = _index_names(inspector, EXTERNAL_ALERT_TABLE)
    indexes = {
        'ix_external_alert_uuid': ['uuid'],
        'ix_external_alert_case_id': ['case_id'],
        'ix_external_alert_message': ['message'],
        'ix_external_alert_status': ['status'],
        'ix_external_alert_creation_date': ['creation_date'],
        'ix_external_alert_is_read': ['is_read'],
        'ix_external_alert_title': ['title'],
        'ix_external_alert_severity': ['severity'],
        'ix_external_alert_category': ['category'],
        'ix_external_alert_tlp': ['tlp'],
        'ix_external_alert_source': ['source'],
        'ix_external_alert_source_ref': ['source_ref'],
        'ix_external_alert_connector_instance_id': ['connector_instance_id'],
        'ix_external_alert_owner_user_id': ['owner_user_id'],
        'ix_external_alert_owner_org_id': ['owner_org_id'],
        'ix_external_alert_review_status': ['review_status'],
        'ix_external_alert_reviewed_by_id': ['reviewed_by_id'],
        'ix_external_alert_reviewed_at': ['reviewed_at'],
        'ix_external_alert_event_time': ['event_time'],
        'ix_external_alert_last_seen': ['last_seen'],
        'ix_external_alert_deduplication_key': ['deduplication_key'],
    }
    with op.batch_alter_table(EXTERNAL_ALERT_TABLE, schema=None) as batch_op:
        for index_name, fields in indexes.items():
            if index_name not in existing_indexes:
                batch_op.create_index(index_name, fields, unique=False)


def _create_external_alert_action_table(inspector):
    if EXTERNAL_ALERT_ACTION_TABLE in inspector.get_table_names():
        return

    op.create_table(
        EXTERNAL_ALERT_ACTION_TABLE,
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def _create_external_alert_action_indexes(inspector):
    existing_indexes = _index_names(inspector, EXTERNAL_ALERT_ACTION_TABLE)
    indexes = {
        'ix_external_alert_action_alert_id': ['alert_id'],
        'ix_external_alert_action_action': ['action'],
        'ix_external_alert_action_user_id': ['user_id'],
        'ix_external_alert_action_created_at': ['created_at'],
    }
    with op.batch_alter_table(EXTERNAL_ALERT_ACTION_TABLE, schema=None) as batch_op:
        for index_name, fields in indexes.items():
            if index_name not in existing_indexes:
                batch_op.create_index(index_name, fields, unique=False)


def _sql_value_for_missing_column(column_name):
    defaults = {
        'uuid': "NULL",
        'status': "'new'",
        'creation_date': "CURRENT_TIMESTAMP",
        'is_read': "FALSE",
        'severity': "'info'",
        'review_status': "'new'",
        'last_seen': "CURRENT_TIMESTAMP",
        'occurrence_count': "1",
    }
    return defaults.get(column_name, "NULL")


def _copy_existing_external_rows(bind, inspector):
    if 'alert' not in inspector.get_table_names():
        return

    alert_columns = set(_column_names(inspector, 'alert'))
    if 'alert_type' not in alert_columns:
        return

    select_columns = []
    for column_name in EXTERNAL_ALERT_COLUMNS:
        if column_name in alert_columns:
            select_columns.append(column_name)
        else:
            select_columns.append(_sql_value_for_missing_column(column_name))

    op.execute(
        sa.text(
            f"""
            INSERT INTO {EXTERNAL_ALERT_TABLE} ({', '.join(EXTERNAL_ALERT_COLUMNS)})
            SELECT {', '.join(select_columns)}
            FROM alert
            WHERE alert_type = 'external'
              AND NOT EXISTS (
                  SELECT 1
                  FROM {EXTERNAL_ALERT_TABLE}
                  WHERE {EXTERNAL_ALERT_TABLE}.id = alert.id
              )
            """
        )
    )

    if bind.dialect.name == 'postgresql':
        op.execute(
            sa.text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{EXTERNAL_ALERT_TABLE}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {EXTERNAL_ALERT_TABLE}), 1),
                    (SELECT COUNT(*) > 0 FROM {EXTERNAL_ALERT_TABLE})
                )
                """
            )
        )

    op.execute("DELETE FROM alert WHERE alert_type = 'external'")


def _drop_external_columns_from_alert(inspector):
    if 'alert' not in inspector.get_table_names():
        return

    existing_indexes = _index_names(inspector, 'alert')
    with op.batch_alter_table('alert', schema=None) as batch_op:
        for index_name in ALERT_EXTERNAL_INDEXES:
            if index_name in existing_indexes:
                batch_op.drop_index(index_name)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = _column_names(inspector, 'alert')
    with op.batch_alter_table('alert', schema=None) as batch_op:
        for column_name in reversed(ALERT_EXTERNAL_COLUMNS):
            if column_name in existing_columns:
                batch_op.drop_column(column_name)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _create_external_alert_table(inspector)

    inspector = sa.inspect(bind)
    _create_external_alert_indexes(inspector)

    inspector = sa.inspect(bind)
    _create_external_alert_action_table(inspector)

    inspector = sa.inspect(bind)
    _create_external_alert_action_indexes(inspector)

    _copy_existing_external_rows(bind, inspector)

    inspector = sa.inspect(bind)
    _drop_external_columns_from_alert(inspector)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if EXTERNAL_ALERT_ACTION_TABLE in inspector.get_table_names():
        op.drop_table(EXTERNAL_ALERT_ACTION_TABLE)

    inspector = sa.inspect(bind)
    if EXTERNAL_ALERT_TABLE in inspector.get_table_names():
        op.drop_table(EXTERNAL_ALERT_TABLE)
