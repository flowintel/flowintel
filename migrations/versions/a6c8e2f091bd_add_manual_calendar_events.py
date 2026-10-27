"""Add standalone calendar events.

Revision ID: a6c8e2f091bd
Revises: 4f62a1b8c9d0
Create Date: 2026-09-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'a6c8e2f091bd'
down_revision = '4f62a1b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'calendar__event',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('start', sa.DateTime(), nullable=False),
        sa.Column('end', sa.DateTime(), nullable=True),
        sa.Column('all_day', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['org.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_calendar__event_user_id', 'calendar__event', ['user_id'])
    op.create_index('ix_calendar__event_org_id', 'calendar__event', ['org_id'])
    op.create_index('ix_calendar__event_start', 'calendar__event', ['start'])


def downgrade():
    op.drop_table('calendar__event')
