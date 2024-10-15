"""empty message

Revision ID: 3a0416665c4b
Revises: b517c582523f
Create Date: 2024-10-10 10:55:53.224114

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = '3a0416665c4b'
down_revision = 'b517c582523f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('task', schema=None) as batch_op:
            batch_op.add_column(sa.Column('time_required', sa.String(), nullable=True))
    except OperationalError:
        print("Column 'time_required' already exist in 'task'")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('task', schema=None) as batch_op:
            batch_op.drop_column('time_required')
    except OperationalError:
        print("Column 'time_required' already dropped")

    # ### end Alembic commands ###