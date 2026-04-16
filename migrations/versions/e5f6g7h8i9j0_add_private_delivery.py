"""Add private delivery mode to scheduled_job

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-04-17 00:03:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('scheduled_job') as batch_op:
        batch_op.add_column(
            sa.Column('delivery_mode', sa.String(length=20), nullable=False, server_default='channel')
        )
        batch_op.add_column(
            sa.Column('team_id', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('selected_members', sa.Text(), nullable=True)
        )
        batch_op.create_foreign_key('fk_scheduled_job_team', 'team', ['team_id'], ['id'])
        # Make channel_id nullable for private-mode jobs
        batch_op.alter_column('channel_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table('scheduled_job') as batch_op:
        batch_op.alter_column('channel_id', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_constraint('fk_scheduled_job_team', type_='foreignkey')
        batch_op.drop_column('selected_members')
        batch_op.drop_column('team_id')
        batch_op.drop_column('delivery_mode')
