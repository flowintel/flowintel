"""empty message

Revision ID: d46002a5f863
Revises: 698d53567382
Create Date: 2025-07-28 14:23:48.589797

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = 'd46002a5f863'
down_revision = '698d53567382'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('task__url__tool', schema=None) as batch_op:
            batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
            batch_op.create_index(batch_op.f('ix_task__url__tool_uuid'), ['uuid'], unique=False)
    except OperationalError:
        print("Column 'uuid' already exist in 'task__url__tool'")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('task__url__tool', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_task__url__tool_uuid'))
            batch_op.drop_column('uuid')
    except OperationalError:
        print("Column 'uuid' already dropped from 'task__url__tool'")

    # ### end Alembic commands ###
