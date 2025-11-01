"""Initial baseline migration with all auth tables

Revision ID: 0001
Revises:
Create Date: 2025-01-31

This migration creates all authentication and tracking tables:
- users: User accounts (phone number as PK)
- guest_sessions: Guest tracking by UUID with IP fallback
- search_sessions: Individual search session tracking
- conversation_history: Complete workflow JSON storage
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '0001'
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
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.TIMESTAMP(), nullable=True),
        sa.Column('total_sessions', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('phone_number')
    )
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=False)

    # Create guest_sessions table
    op.create_table(
        'guest_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('guest_uuid', sa.String(length=36), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_count', sa.Integer(), nullable=True),
        sa.Column('last_session_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_guest_uuid', 'guest_sessions', ['guest_uuid'], unique=False)
    op.create_index('ix_guest_ip', 'guest_sessions', ['ip_address'], unique=False)
    op.create_unique_constraint('uq_guest_sessions_guest_uuid', 'guest_sessions', ['guest_uuid'])

    # Create search_sessions table
    op.create_table(
        'search_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=True),
        sa.Column('guest_uuid', sa.String(length=36), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('search_type', sa.String(length=10), nullable=True),
        sa.Column('search_input', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_search_sessions_phone_number'), 'search_sessions', ['phone_number'], unique=False)
    op.create_index(op.f('ix_search_sessions_guest_uuid'), 'search_sessions', ['guest_uuid'], unique=False)
    op.create_index(op.f('ix_search_sessions_ip_address'), 'search_sessions', ['ip_address'], unique=False)
    op.create_index(op.f('ix_search_sessions_session_id'), 'search_sessions', ['session_id'], unique=False)

    # Create conversation_history table
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=True),
        sa.Column('guest_uuid', sa.String(length=36), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('conversation_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number', 'session_id', name='uq_conversation_phone_session'),
        sa.UniqueConstraint('guest_uuid', 'session_id', name='uq_conversation_guest_session')
    )
    op.create_index('ix_conversation_phone', 'conversation_history', ['phone_number'], unique=False)
    op.create_index('ix_conversation_guest', 'conversation_history', ['guest_uuid'], unique=False)
    op.create_index('ix_conversation_session', 'conversation_history', ['session_id'], unique=False)


def downgrade():
    # Drop conversation_history table
    op.drop_index('ix_conversation_session', table_name='conversation_history')
    op.drop_index('ix_conversation_guest', table_name='conversation_history')
    op.drop_index('ix_conversation_phone', table_name='conversation_history')
    op.drop_table('conversation_history')

    # Drop search_sessions table
    op.drop_index(op.f('ix_search_sessions_session_id'), table_name='search_sessions')
    op.drop_index(op.f('ix_search_sessions_ip_address'), table_name='search_sessions')
    op.drop_index(op.f('ix_search_sessions_guest_uuid'), table_name='search_sessions')
    op.drop_index(op.f('ix_search_sessions_phone_number'), table_name='search_sessions')
    op.drop_table('search_sessions')

    # Drop guest_sessions table
    op.drop_constraint('uq_guest_sessions_guest_uuid', 'guest_sessions', type_='unique')
    op.drop_index('ix_guest_ip', table_name='guest_sessions')
    op.drop_index('ix_guest_uuid', table_name='guest_sessions')
    op.drop_table('guest_sessions')

    # Drop users table
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_table('users')
