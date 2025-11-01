"""Add login_attempts table for rate limiting

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-31
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    # Create login_attempts table for rate limiting
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('attempt_type', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_login_attempts_phone', 'login_attempts', ['phone_number'], unique=False)
    op.create_index('ix_login_attempts_created', 'login_attempts', ['created_at'], unique=False)


def downgrade():
    op.drop_index('ix_login_attempts_created', table_name='login_attempts')
    op.drop_index('ix_login_attempts_phone', table_name='login_attempts')
    op.drop_table('login_attempts')
