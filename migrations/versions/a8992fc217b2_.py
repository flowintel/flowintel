"""empty message

Revision ID: a8992fc217b2
Revises: 73b8cc4d3c54
Create Date: 2023-12-07 10:12:54.353206

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8992fc217b2'
down_revision = '73b8cc4d3c54'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.drop_column('expanded')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expanded', sa.VARCHAR(), nullable=True))

    # ### end Alembic commands ###