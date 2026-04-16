"""Add job_log table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-04-17 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'job_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(length=20), nullable=True, server_default='scheduled'),
        sa.ForeignKeyConstraint(['job_id'], ['scheduled_job.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_log_job_executed', 'job_log', ['job_id', 'executed_at'])


def downgrade():
    op.drop_index('ix_job_log_job_executed', table_name='job_log')
    op.drop_table('job_log')
