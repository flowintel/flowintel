"""Add User.last_login and Login_Event table

Revision ID: d27a4e1b9c83
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd27a4e1b9c83'
down_revision = '322c78d73617'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = [c['name'] for c in inspector.get_columns('user')]
    if 'last_login' not in user_columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('last_login', sa.DateTime(), nullable=True))
            batch_op.create_index(batch_op.f('ix_user_last_login'), ['last_login'], unique=False)

    if 'login__event' not in inspector.get_table_names():
        op.create_table(
            'login__event',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('login_date', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('login__event', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_login__event_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_login__event_login_date'), ['login_date'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'login__event' in inspector.get_table_names():
        with op.batch_alter_table('login__event', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_login__event_login_date'))
            batch_op.drop_index(batch_op.f('ix_login__event_user_id'))
        op.drop_table('login__event')

    user_columns = [c['name'] for c in inspector.get_columns('user')]
    if 'last_login' in user_columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_user_last_login'))
            batch_op.drop_column('last_login')
