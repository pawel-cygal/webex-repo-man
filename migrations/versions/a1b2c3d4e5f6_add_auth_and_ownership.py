"""Add user, app_setting, and owner_id columns

Revision ID: a1b2c3d4e5f6
Revises: 54d7c9f7f812
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '54d7c9f7f812'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('webex_id', sa.String(length=255), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_super_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('webex_id'),
    )
    op.create_index('ix_user_email', 'user', ['email'])

    op.create_table(
        'app_setting',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('key'),
    )

    # SQLite cannot ADD COLUMN with FOREIGN KEY directly. Use batch_alter_table
    # so Alembic recreates the tables behind the scenes on SQLite, while still
    # producing a proper ALTER on engines that support it.
    with op.batch_alter_table('webex_channel') as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_webex_channel_owner', 'user', ['owner_id'], ['id'])

    with op.batch_alter_table('scheduled_job') as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_scheduled_job_owner', 'user', ['owner_id'], ['id'])


def downgrade():
    with op.batch_alter_table('scheduled_job') as batch_op:
        batch_op.drop_constraint('fk_scheduled_job_owner', type_='foreignkey')
        batch_op.drop_column('owner_id')

    with op.batch_alter_table('webex_channel') as batch_op:
        batch_op.drop_constraint('fk_webex_channel_owner', type_='foreignkey')
        batch_op.drop_column('owner_id')

    op.drop_table('app_setting')
    op.drop_index('ix_user_email', table_name='user')
    op.drop_table('user')
