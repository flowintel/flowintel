"""empty message

Revision ID: 72883f4859bf
Revises: 9ffdc12e43a9
Create Date: 2024-08-07 09:40:38.372768

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = '72883f4859bf'
down_revision = '9ffdc12e43a9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        op.create_table('case__link__case',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id_1', sa.Integer(), nullable=True),
        sa.Column('case_id_2', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('case__link__case', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_case__link__case_case_id_1'), ['case_id_1'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__link__case_case_id_2'), ['case_id_2'], unique=False)
    except OperationalError:
        print("Table 'case__link__case' already exist")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case__link__case', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_case__link__case_case_id_2'))
        batch_op.drop_index(batch_op.f('ix_case__link__case_case_id_1'))

    op.drop_table('case__link__case')
    # ### end Alembic commands ###
