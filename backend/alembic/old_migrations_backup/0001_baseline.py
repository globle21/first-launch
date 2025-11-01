"""baseline schema for phone-only auth + guest uuid

Revision ID: 0001
Revises: 
Create Date: 2025-10-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing tables if they exist (order matters)
    op.execute('DROP TABLE IF EXISTS conversation_history CASCADE')
    op.execute('DROP TABLE IF EXISTS search_sessions CASCADE')
    op.execute('DROP TABLE IF EXISTS guest_sessions CASCADE')
    op.execute('DROP TABLE IF EXISTS otp_requests CASCADE')
    op.execute('DROP TABLE IF EXISTS users CASCADE')

    # users
    op.create_table(
        'users',
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('country_code', sa.String(length=5), nullable=True, server_default='+91'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('last_login', sa.TIMESTAMP(), nullable=True),
        sa.Column('total_sessions', sa.Integer(), server_default='0', nullable=True),
        sa.PrimaryKeyConstraint('phone_number')
    )
    op.create_index('ix_users_phone_number', 'users', ['phone_number'], unique=False)

    # guest_sessions (IP-based limit tracking)
    op.create_table(
        'guest_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('last_session_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ip_address')
    )
    op.create_index('ix_guest_sessions_ip_address', 'guest_sessions', ['ip_address'], unique=False)

    # search_sessions (per search run) with optional phone_number or guest_uuid
    op.create_table(
        'search_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=True),
        sa.Column('guest_uuid', sa.String(length=36), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('search_type', sa.String(length=10), nullable=True),
        sa.Column('search_input', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index('ix_search_sessions_phone_number', 'search_sessions', ['phone_number'], unique=False)
    op.create_index('ix_search_sessions_guest_uuid', 'search_sessions', ['guest_uuid'], unique=False)
    op.create_index('ix_search_sessions_ip_address', 'search_sessions', ['ip_address'], unique=False)
    op.create_index('ix_search_sessions_session_id', 'search_sessions', ['session_id'], unique=False)

    # conversation_history: supports user or guest owner
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=True),
        sa.Column('guest_uuid', sa.String(length=36), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('conversation_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_phone', 'conversation_history', ['phone_number'], unique=False)
    op.create_index('ix_conversation_guest', 'conversation_history', ['guest_uuid'], unique=False)
    op.create_index('ix_conversation_session', 'conversation_history', ['session_id'], unique=False)
    op.create_unique_constraint('uq_conversation_phone_session', 'conversation_history', ['phone_number', 'session_id'])
    op.create_unique_constraint('uq_conversation_guest_session', 'conversation_history', ['guest_uuid', 'session_id'])


def downgrade():
    op.drop_constraint('uq_conversation_guest_session', 'conversation_history', type_='unique')
    op.drop_constraint('uq_conversation_phone_session', 'conversation_history', type_='unique')
    op.drop_index('ix_conversation_session', table_name='conversation_history')
    op.drop_index('ix_conversation_guest', table_name='conversation_history')
    op.drop_index('ix_conversation_phone', table_name='conversation_history')
    op.drop_table('conversation_history')

    op.drop_index('ix_search_sessions_session_id', table_name='search_sessions')
    op.drop_index('ix_search_sessions_ip_address', table_name='search_sessions')
    op.drop_index('ix_search_sessions_guest_uuid', table_name='search_sessions')
    op.drop_index('ix_search_sessions_phone_number', table_name='search_sessions')
    op.drop_table('search_sessions')

    op.drop_index('ix_guest_sessions_ip_address', table_name='guest_sessions')
    op.drop_table('guest_sessions')

    op.drop_index('ix_users_phone_number', table_name='users')
    op.drop_table('users')


