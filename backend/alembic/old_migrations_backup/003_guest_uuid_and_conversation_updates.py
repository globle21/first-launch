"""add guest_uuid and conversation history updates

Revision ID: 003
Revises: 002
Create Date: 2025-10-31
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add guest_uuid to search_sessions
    with op.batch_alter_table('search_sessions') as batch_op:
        batch_op.add_column(sa.Column('guest_uuid', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_search_sessions_guest_uuid', ['guest_uuid'], unique=False)

    # ConversationHistory changes: add id PK, add guest_uuid, relax phone_number to nullable, add unique constraints
    # Add columns first
    op.add_column('conversation_history', sa.Column('id', sa.Integer(), autoincrement=True, nullable=True))
    op.add_column('conversation_history', sa.Column('guest_uuid', sa.String(length=36), nullable=True))

    # Create indexes
    op.create_index('ix_conversation_guest', 'conversation_history', ['guest_uuid'], unique=False)

    # Drop old PK (phone_number, session_id) and create new PK on id
    op.drop_constraint('conversation_history_pkey', 'conversation_history', type_='primary')
    op.create_primary_key('pk_conversation_history', 'conversation_history', ['id'])

    # Make phone_number nullable (dialect-safe: alter column)
    with op.batch_alter_table('conversation_history') as batch_op:
        batch_op.alter_column('phone_number', existing_type=sa.String(length=15), nullable=True)

    # Add unique constraints for phone+session and guest+session
    op.create_unique_constraint('uq_conversation_phone_session', 'conversation_history', ['phone_number', 'session_id'])
    op.create_unique_constraint('uq_conversation_guest_session', 'conversation_history', ['guest_uuid', 'session_id'])


def downgrade():
    # Remove unique constraints
    op.drop_constraint('uq_conversation_guest_session', 'conversation_history', type_='unique')
    op.drop_constraint('uq_conversation_phone_session', 'conversation_history', type_='unique')

    # Revert phone_number to NOT NULL (best-effort)
    with op.batch_alter_table('conversation_history') as batch_op:
        batch_op.alter_column('phone_number', existing_type=sa.String(length=15), nullable=False)

    # Drop new PK and restore old composite PK
    op.drop_constraint('pk_conversation_history', 'conversation_history', type_='primary')
    op.create_primary_key('conversation_history_pkey', 'conversation_history', ['phone_number', 'session_id'])

    # Drop added columns and indexes
    op.drop_index('ix_conversation_guest', table_name='conversation_history')
    op.drop_column('conversation_history', 'guest_uuid')
    op.drop_column('conversation_history', 'id')

    # Remove guest_uuid from search_sessions
    with op.batch_alter_table('search_sessions') as batch_op:
        batch_op.drop_index('ix_search_sessions_guest_uuid')
        batch_op.drop_column('guest_uuid')


