"""Add MISP object reference table

Revision ID: 4f62a1b8c9d0
Revises: 8d9f2a4c6b10
Create Date: 2026-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '4f62a1b8c9d0'
down_revision = '8d9f2a4c6b10'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'case__misp__object__reference' not in inspector.get_table_names():
        op.create_table(
            'case__misp__object__reference',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('case_id', sa.Integer(), nullable=True),
            sa.Column('source_object_id', sa.Integer(), nullable=True),
            sa.Column('source_attribute_id', sa.Integer(), nullable=True),
            sa.Column('referenced_object_id', sa.Integer(), nullable=True),
            sa.Column('referenced_attribute_id', sa.Integer(), nullable=True),
            sa.Column('relationship_type', sa.String(length=128), nullable=True),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('creation_date', sa.DateTime(), nullable=True),
            sa.Column('last_modif', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['case_id'], ['case.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_object_id'], ['case__misp__object.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_attribute_id'], ['misp__attribute.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['referenced_object_id'], ['case__misp__object.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['referenced_attribute_id'], ['misp__attribute.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint(
                'source_object_id',
                'source_attribute_id',
                'referenced_object_id',
                'referenced_attribute_id',
                'relationship_type',
                name='uq_case_misp_object_reference'
            )
        )
        with op.batch_alter_table('case__misp__object__reference', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_case_id'), ['case_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_source_object_id'), ['source_object_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_source_attribute_id'), ['source_attribute_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_referenced_object_id'), ['referenced_object_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_referenced_attribute_id'), ['referenced_attribute_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_relationship_type'), ['relationship_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_creation_date'), ['creation_date'], unique=False)
            batch_op.create_index(batch_op.f('ix_case__misp__object__reference_last_modif'), ['last_modif'], unique=False)
    else:
        columns = {column['name'] for column in inspector.get_columns('case__misp__object__reference')}
        indexes = {index['name'] for index in inspector.get_indexes('case__misp__object__reference')}
        with op.batch_alter_table('case__misp__object__reference', schema=None) as batch_op:
            if 'source_attribute_id' not in columns:
                batch_op.add_column(sa.Column('source_attribute_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    'fk_case_misp_object_reference_source_attribute_id_misp_attribute',
                    'misp__attribute',
                    ['source_attribute_id'],
                    ['id'],
                    ondelete='CASCADE',
                )
            if 'referenced_attribute_id' not in columns:
                batch_op.add_column(sa.Column('referenced_attribute_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    'fk_case_misp_object_reference_referenced_attribute_id_misp_attribute',
                    'misp__attribute',
                    ['referenced_attribute_id'],
                    ['id'],
                    ondelete='CASCADE',
                )
            if 'ix_case__misp__object__reference_source_attribute_id' not in indexes:
                batch_op.create_index(batch_op.f('ix_case__misp__object__reference_source_attribute_id'), ['source_attribute_id'], unique=False)
            if 'ix_case__misp__object__reference_referenced_attribute_id' not in indexes:
                batch_op.create_index(batch_op.f('ix_case__misp__object__reference_referenced_attribute_id'), ['referenced_attribute_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'case__misp__object__reference' in inspector.get_table_names():
        op.drop_table('case__misp__object__reference')
