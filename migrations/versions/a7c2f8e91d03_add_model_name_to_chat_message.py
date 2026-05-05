"""add model_name to chat_message

Revision ID: a7c2f8e91d03
Revises: dde56729b9d4
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa
import uuid as _uuid

revision = 'a7c2f8e91d03'
down_revision = 'dde56729b9d4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('chat_message')]

    if 'model_name' not in existing_columns:
        with op.batch_alter_table('chat_message', schema=None) as batch_op:
            batch_op.add_column(sa.Column('model_name', sa.String(length=100), nullable=True))

    if 'uuid' not in existing_columns:
        with op.batch_alter_table('chat_conversation', schema=None) as batch_op:
            batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))

        # Backfill existing rows with unique UUIDs
        bind = op.get_bind()
        rows = bind.execute(sa.text('SELECT id FROM chat_conversation')).fetchall()
        for row in rows:
            bind.execute(
                sa.text('UPDATE chat_conversation SET uuid = :u WHERE id = :id'),
                {'u': str(_uuid.uuid4()), 'id': row[0]}
            )

        with op.batch_alter_table('chat_conversation', schema=None) as batch_op:
            batch_op.create_index('ix_chat_conversation_uuid', ['uuid'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('chat_message')]

    if 'model_name' in existing_columns:
        with op.batch_alter_table('chat_message', schema=None) as batch_op:
            batch_op.drop_column('model_name')

    if 'uuid' in existing_columns:
        with op.batch_alter_table('chat_conversation', schema=None) as batch_op:
            batch_op.drop_index('ix_chat_conversation_uuid')
            batch_op.drop_column('uuid')
