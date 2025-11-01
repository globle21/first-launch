"""initial auth tables

Revision ID: 001
Revises:
Create Date: 2025-01-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('country_code', sa.String(length=5), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('last_login', sa.TIMESTAMP(), nullable=True),
        sa.Column('total_sessions', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('phone_number')
    )
    op.create_index('ix_users_phone_number', 'users', ['phone_number'], unique=False)

    # Create otp_requests table
    op.create_table(
        'otp_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('otp_code', sa.String(length=6), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verification_attempts', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_otp_requests_created_at', 'otp_requests', ['created_at'], unique=False)
    op.create_index('ix_otp_requests_expires_at', 'otp_requests', ['expires_at'], unique=False)
    op.create_index('ix_otp_requests_phone_number', 'otp_requests', ['phone_number'], unique=False)

    # Create guest_sessions table
    op.create_table(
        'guest_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_count', sa.Integer(), nullable=True),
        sa.Column('last_session_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ip_address')
    )
    op.create_index('ix_guest_sessions_ip_address', 'guest_sessions', ['ip_address'], unique=False)

    # Create search_sessions table
    op.create_table(
        'search_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('search_type', sa.String(length=10), nullable=True),
        sa.Column('search_input', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index('ix_search_sessions_ip_address', 'search_sessions', ['ip_address'], unique=False)
    op.create_index('ix_search_sessions_phone_number', 'search_sessions', ['phone_number'], unique=False)
    op.create_index('ix_search_sessions_session_id', 'search_sessions', ['session_id'], unique=False)


def downgrade():
    # Drop all tables
    op.drop_table('search_sessions')
    op.drop_table('guest_sessions')
    op.drop_table('otp_requests')
    op.drop_table('users')
