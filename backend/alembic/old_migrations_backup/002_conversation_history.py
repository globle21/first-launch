"""add conversation history table

Revision ID: 002
Revises: 001
Create Date: 2025-01-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create conversation_history table
    op.create_table(
        'conversation_history',
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('conversation_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('phone_number', 'session_id')
    )
    op.create_index('ix_conversation_phone', 'conversation_history', ['phone_number'], unique=False)
    op.create_index('ix_conversation_session', 'conversation_history', ['session_id'], unique=False)


def downgrade():
    # Drop conversation_history table
    op.drop_index('ix_conversation_session', table_name='conversation_history')
    op.drop_index('ix_conversation_phone', table_name='conversation_history')
    op.drop_table('conversation_history')
