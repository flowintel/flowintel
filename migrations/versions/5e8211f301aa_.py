"""empty message

Revision ID: 5e8211f301aa
Revises: a95e730510d6
Create Date: 2026-03-03 10:46:34.263836

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e8211f301aa'
down_revision = 'a95e730510d6'
branch_labels = None
depends_on = None


def upgrade():
    # safety-guarded commands: only add columns/indexes if they do not already exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = [c['name'] for c in inspector.get_columns('case')]
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('case')]

    with op.batch_alter_table('case', schema=None) as batch_op:
        if 'computer_assistate_model' not in existing_cols:
            batch_op.add_column(sa.Column('computer_assistate_model', sa.String(), nullable=True))
        if 'computer_assistate_prompt' not in existing_cols:
            batch_op.add_column(sa.Column('computer_assistate_prompt', sa.Text(), nullable=True))

        # create indexes only if they're missing
        ix_is_private = batch_op.f('ix_case_is_private')
        ix_privileged = batch_op.f('ix_case_privileged_case')
        if ix_is_private not in existing_indexes:
            batch_op.create_index(ix_is_private, ['is_private'], unique=False)
        if ix_privileged not in existing_indexes:
            batch_op.create_index(ix_privileged, ['privileged_case'], unique=False)

    # end guarded commands


def downgrade():
    # guarded downgrade: only drop if present
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = [c['name'] for c in inspector.get_columns('case')]
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('case')]

    with op.batch_alter_table('case', schema=None) as batch_op:
        ix_privileged = batch_op.f('ix_case_privileged_case')
        ix_is_private = batch_op.f('ix_case_is_private')
        if ix_privileged in existing_indexes:
            batch_op.drop_index(ix_privileged)
        if ix_is_private in existing_indexes:
            batch_op.drop_index(ix_is_private)

        if 'computer_assistate_prompt' in existing_cols:
            batch_op.drop_column('computer_assistate_prompt')
        if 'computer_assistate_model' in existing_cols:
            batch_op.drop_column('computer_assistate_model')

    # end guarded downgrade
