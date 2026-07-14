"""add_shared_org_id_and_sharing_scope_to_connector_instance

Revision ID: 0f3c7b8a1d22
Revises: 67847bdca48b
Create Date: 2026-07-14 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f3c7b8a1d22'
down_revision = '67847bdca48b'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("connector__instance")}

    if "shared_org_id" not in columns:
        with op.batch_alter_table('connector__instance', schema=None) as batch_op:
            batch_op.add_column(sa.Column('shared_org_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f('ix_connector__instance_shared_org_id'), ['shared_org_id'], unique=False)

    if "sharing_scope" not in columns:
        with op.batch_alter_table('connector__instance', schema=None) as batch_op:
            batch_op.add_column(sa.Column('sharing_scope', sa.String(length=20), nullable=False, server_default='personal'))
            batch_op.create_index(batch_op.f('ix_connector__instance_sharing_scope'), ['sharing_scope'], unique=False)

    op.execute("""
        UPDATE connector__instance
        SET sharing_scope = CASE
            WHEN shared_org_id IS NOT NULL THEN 'org'
            WHEN global_api_key IS NOT NULL AND global_api_key != '' THEN 'global'
            ELSE 'personal'
        END
    """)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("connector__instance")}

    if "sharing_scope" in columns:
        with op.batch_alter_table('connector__instance', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_connector__instance_sharing_scope'))
            batch_op.drop_column('sharing_scope')

    if "shared_org_id" in columns:
        with op.batch_alter_table('connector__instance', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_connector__instance_shared_org_id'))
            batch_op.drop_column('shared_org_id')
