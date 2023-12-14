"""empty message

Revision ID: 04ee0d5e0abb
Revises: 85e79b40ca2e
Create Date: 2023-11-29 11:40:27.185464

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04ee0d5e0abb'
down_revision = '85e79b40ca2e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('connector',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('url', sa.String(length=64), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('icon_id', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('connector', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_connector_icon_id'), ['icon_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_connector_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_connector_url'), ['url'], unique=False)

    op.create_table('connector__icon',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('uuid', sa.String(length=36), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('connector__icon', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_connector__icon_name'), ['name'], unique=True)
        batch_op.create_index(batch_op.f('ix_connector__icon_uuid'), ['uuid'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('connector__icon', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_connector__icon_uuid'))
        batch_op.drop_index(batch_op.f('ix_connector__icon_name'))

    op.drop_table('connector__icon')
    with op.batch_alter_table('connector', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_connector_url'))
        batch_op.drop_index(batch_op.f('ix_connector_name'))
        batch_op.drop_index(batch_op.f('ix_connector_icon_id'))

    op.drop_table('connector')
    # ### end Alembic commands ###