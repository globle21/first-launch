"""add guest_uuid to guest_sessions for accurate tracking

Revision ID: 004
Revises: 0001
Create Date: 2025-01-XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '0001'  # Update this to the latest migration if needed
branch_labels = None
depends_on = None


def upgrade():
    # Add guest_uuid column to guest_sessions
    op.add_column('guest_sessions', sa.Column('guest_uuid', sa.String(length=36), nullable=True))
    
    # Remove the unique constraint on ip_address (since multiple users can share IP via NAT)
    op.drop_constraint('guest_sessions_ip_address_key', 'guest_sessions', type_='unique')
    
    # Create unique constraint on guest_uuid (each guest has unique UUID)
    op.create_unique_constraint('uq_guest_sessions_guest_uuid', 'guest_sessions', ['guest_uuid'])
    
    # Create indexes
    op.create_index('ix_guest_uuid', 'guest_sessions', ['guest_uuid'], unique=False)
    op.create_index('ix_guest_ip', 'guest_sessions', ['ip_address'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_guest_ip', table_name='guest_sessions')
    op.drop_index('ix_guest_uuid', table_name='guest_sessions')
    
    # Drop unique constraint on guest_uuid
    op.drop_constraint('uq_guest_sessions_guest_uuid', 'guest_sessions', type_='unique')
    
    # Restore unique constraint on ip_address
    op.create_unique_constraint('guest_sessions_ip_address_key', 'guest_sessions', ['ip_address'])
    
    # Remove guest_uuid column
    op.drop_column('guest_sessions', 'guest_uuid')

