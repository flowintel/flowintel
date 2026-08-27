"""Add notification category and type

Revision ID: 6e947c30e21c
Revises: c2f6a8d9e0b1
Create Date: 2026-08-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '6e947c30e21c'
down_revision = 'c2f6a8d9e0b1'
branch_labels = None
depends_on = None


def _column_names(inspector, table_name):
    return [col['name'] for col in inspector.get_columns(table_name)]


def _index_names(inspector, table_name):
    return [idx['name'] for idx in inspector.get_indexes(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    if 'notification' not in existing_tables:
        return

    existing_columns = _column_names(inspector, 'notification')
    with op.batch_alter_table('notification', schema=None) as batch_op:
        if 'category' not in existing_columns:
            batch_op.add_column(sa.Column('category', sa.String(length=40), nullable=True))
        if 'notification_type' not in existing_columns:
            batch_op.add_column(sa.Column('notification_type', sa.String(length=40), nullable=True))
        if 'target_url' not in existing_columns:
            batch_op.add_column(sa.Column('target_url', sa.String(8192), nullable=True))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, 'notification')
    with op.batch_alter_table('notification', schema=None) as batch_op:
        if 'ix_notification_category' not in existing_indexes:
            batch_op.create_index('ix_notification_category', ['category'], unique=False)
        if 'ix_notification_notification_type' not in existing_indexes:
            batch_op.create_index('ix_notification_notification_type', ['notification_type'], unique=False)

    op.execute("""
        UPDATE notification
        SET category = CASE
            WHEN case_id < 0
                OR LOWER(COALESCE(message, '')) LIKE '%password reset%'
                OR LOWER(COALESCE(message, '')) LIKE '%keycloak user%'
                OR LOWER(COALESCE(message, '')) LIKE '%entra user%'
                OR LOWER(COALESCE(message, '')) LIKE '%single sign-on%'
                OR LOWER(COALESCE(message, '')) LIKE '%provisioned%'
                OR html_icon IN ('fa-solid fa-key', 'fa-solid fa-user-shield')
                THEN 'admin'
            WHEN LOWER(COALESCE(message, '')) LIKE '%days remains%'
                OR LOWER(COALESCE(message, '')) LIKE '%deadline%'
                OR LOWER(COALESCE(message, '')) LIKE '%reminder%'
                OR html_icon IN ('fa-solid fa-radiation', 'fa-solid fa-skull-crossbones', 'fa-solid fa-clock')
                THEN 'deadline'
            WHEN LOWER(COALESCE(message, '')) LIKE '%new alert received%'
                OR html_icon = 'fa-solid fa-triangle-exclamation'
                THEN 'alerting'
            WHEN LOWER(COALESCE(message, '')) LIKE '%misp sync collision%'
                OR html_icon = 'fa-solid fa-code-compare'
                THEN 'misp_sync'
            WHEN LOWER(COALESCE(message, '')) LIKE '%analyser run finished%'
                OR LOWER(COALESCE(message, '')) LIKE '%analyzer run finished%'
                THEN 'analyzer'
            WHEN LOWER(COALESCE(message, '')) LIKE '%owner of case%'
                OR LOWER(COALESCE(message, '')) LIKE '% add to case%'
                OR LOWER(COALESCE(message, '')) LIKE '% added to case%'
                OR LOWER(COALESCE(message, '')) LIKE '%removed from case%'
                OR html_icon IN ('fa-solid fa-sitemap', 'fa-solid fa-hand-holding-hand', 'fa-solid fa-door-open')
                THEN 'organisation'
            WHEN LOWER(COALESCE(message, '')) LIKE '%task%'
                OR html_icon IN (
                    'fa-solid fa-hand',
                    'fa-solid fa-handshake-slash',
                    'fa-solid fa-check',
                    'fa-solid fa-heart-circle-bolt',
                    'fa-solid fa-circle-check',
                    'fa-solid fa-circle-xmark',
                    'fa-solid fa-circle-exclamation',
                    'fa-solid fa-magnifying-glass',
                    'fa-solid fa-circle-info',
                    'fa-solid fa-bell'
                )
                THEN 'task'
            WHEN LOWER(COALESCE(message, '')) LIKE '%case%'
                OR html_icon IN ('fa-solid fa-square-check', 'fa-solid fa-heart-circle-plus', 'fa-solid fa-trash')
                THEN 'case'
            ELSE 'general'
        END
        WHERE category IS NULL
    """)
    op.execute("""
        UPDATE notification
        SET notification_type = CASE
            WHEN case_id < 0 OR LOWER(COALESCE(message, '')) LIKE '%password reset%' OR html_icon = 'fa-solid fa-key'
                THEN 'password_reset'
            WHEN LOWER(COALESCE(message, '')) LIKE '%keycloak user%'
                OR LOWER(COALESCE(message, '')) LIKE '%entra user%'
                OR LOWER(COALESCE(message, '')) LIKE '%single sign-on%'
                OR LOWER(COALESCE(message, '')) LIKE '%provisioned%'
                OR html_icon = 'fa-solid fa-user-shield'
                THEN 'provisioning'
            WHEN LOWER(COALESCE(message, '')) LIKE '%days remains%'
                OR LOWER(COALESCE(message, '')) LIKE '%deadline%'
                OR html_icon IN ('fa-solid fa-radiation', 'fa-solid fa-skull-crossbones')
                THEN 'deadline'
            WHEN LOWER(COALESCE(message, '')) LIKE '%reminder%' OR html_icon = 'fa-solid fa-clock'
                THEN 'reminder'
            WHEN LOWER(COALESCE(message, '')) LIKE '%new alert received%' OR html_icon = 'fa-solid fa-triangle-exclamation'
                THEN 'external_alert'
            WHEN LOWER(COALESCE(message, '')) LIKE '%misp sync collision%' OR html_icon = 'fa-solid fa-code-compare'
                THEN 'collision'
            WHEN LOWER(COALESCE(message, '')) LIKE '%analyser run finished%'
                OR LOWER(COALESCE(message, '')) LIKE '%analyzer run finished%'
                THEN 'analysis_completed'
            WHEN LOWER(COALESCE(message, '')) LIKE '%assigned to%' OR html_icon = 'fa-solid fa-hand'
                THEN 'assignment'
            WHEN LOWER(COALESCE(message, '')) LIKE '%assignment have been removed%'
                OR LOWER(COALESCE(message, '')) LIKE '%assignment has been removed%'
                OR html_icon = 'fa-solid fa-handshake-slash'
                THEN 'unassignment'
            WHEN LOWER(COALESCE(message, '')) LIKE '%approved%' OR html_icon = 'fa-solid fa-circle-check'
                THEN 'approval'
            WHEN LOWER(COALESCE(message, '')) LIKE '%rejected%' OR html_icon = 'fa-solid fa-circle-xmark'
                THEN 'rejection'
            WHEN LOWER(COALESCE(message, '')) LIKE '%submitted for review%'
                OR LOWER(COALESCE(message, '')) LIKE '%request review%'
                OR html_icon = 'fa-solid fa-magnifying-glass'
                THEN 'review'
            WHEN LOWER(COALESCE(message, '')) LIKE '%requested%' OR html_icon = 'fa-solid fa-circle-exclamation'
                THEN 'request'
            WHEN LOWER(COALESCE(message, '')) LIKE '%completed%' OR html_icon IN ('fa-solid fa-check', 'fa-solid fa-square-check')
                THEN 'completion'
            WHEN LOWER(COALESCE(message, '')) LIKE '%revived%' OR html_icon IN ('fa-solid fa-heart-circle-plus', 'fa-solid fa-heart-circle-bolt')
                THEN 'revival'
            WHEN LOWER(COALESCE(message, '')) LIKE '%deleted%' OR html_icon = 'fa-solid fa-trash'
                THEN 'deletion'
            WHEN LOWER(COALESCE(message, '')) LIKE '%owner of case%' OR html_icon = 'fa-solid fa-hand-holding-hand'
                THEN 'ownership'
            WHEN LOWER(COALESCE(message, '')) LIKE '% add to case%'
                OR LOWER(COALESCE(message, '')) LIKE '% added to case%'
                OR LOWER(COALESCE(message, '')) LIKE '%removed from case%'
                OR html_icon IN ('fa-solid fa-sitemap', 'fa-solid fa-door-open')
                THEN 'membership'
            WHEN LOWER(COALESCE(message, '')) LIKE '%notify for task%' OR html_icon = 'fa-solid fa-bell'
                THEN 'manual_notice'
            WHEN LOWER(COALESCE(message, '')) LIKE '%task%' OR html_icon = 'fa-solid fa-circle-info'
                THEN 'status'
            ELSE 'info'
        END
        WHERE notification_type IS NULL
    """)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    if 'notification' not in existing_tables:
        return

    existing_indexes = _index_names(inspector, 'notification')
    with op.batch_alter_table('notification', schema=None) as batch_op:
        if 'ix_notification_notification_type' in existing_indexes:
            batch_op.drop_index('ix_notification_notification_type')
        if 'ix_notification_category' in existing_indexes:
            batch_op.drop_index('ix_notification_category')

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = _column_names(inspector, 'notification')
    with op.batch_alter_table('notification', schema=None) as batch_op:
        if 'target_url' in existing_columns:
            batch_op.drop_column('target_url')
        if 'notification_type' in existing_columns:
            batch_op.drop_column('notification_type')
        if 'category' in existing_columns:
            batch_op.drop_column('category')
