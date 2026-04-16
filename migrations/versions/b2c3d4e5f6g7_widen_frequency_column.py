"""Widen frequency column for multi-day schedules

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('scheduled_job') as batch_op:
        batch_op.alter_column(
            'frequency',
            existing_type=sa.String(length=20),
            type_=sa.String(length=128),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table('scheduled_job') as batch_op:
        batch_op.alter_column(
            'frequency',
            existing_type=sa.String(length=128),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
