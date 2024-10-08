"""empty message

Revision ID: 03a283bcdd4b
Revises: 9ee9484a8102
Create Date: 2023-10-27 09:59:05.090340

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = '03a283bcdd4b'
down_revision = '9ee9484a8102'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('case__template', schema=None) as batch_op:
            batch_op.add_column(sa.Column('taxonomies', sa.String(), nullable=True))
    except OperationalError:
        print("Column 'taxonomies' already exist in 'case__template'")

    try:
        with op.batch_alter_table('task__template', schema=None) as batch_op:
            batch_op.add_column(sa.Column('taxonomies', sa.String(), nullable=True))
    except OperationalError:
        print("Column 'taxonomies' already exist in 'task__template'")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task__template', schema=None) as batch_op:
        batch_op.drop_column('taxonomies')

    with op.batch_alter_table('case__template', schema=None) as batch_op:
        batch_op.drop_column('taxonomies')

    # ### end Alembic commands ###
