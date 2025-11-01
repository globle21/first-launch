"""
SQLAlchemy models for authentication
"""
from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP, Text, func, PrimaryKeyConstraint, Index, JSON, UniqueConstraint
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import Base


class User(Base):
    """User model - phone_number is primary key"""
    __tablename__ = "users"
    
    phone_number = Column(String(15), primary_key=True, index=True)
    country_code = Column(String(5), default="+91")
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_login = Column(TIMESTAMP, nullable=True)
    total_sessions = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<User {self.phone_number}>"


# OTPRequest model removed (obsolete)


class GuestSession(Base):
    """Guest session tracking by guest_uuid (primary) or IP (fallback)"""
    __tablename__ = "guest_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guest_uuid = Column(String(36), nullable=True, unique=True, index=True)  # Primary tracking identifier
    ip_address = Column(String(45), nullable=False, index=True)  # Not unique (NAT scenarios)
    user_agent = Column(Text, nullable=True)
    session_count = Column(Integer, default=0)
    last_session_at = Column(TIMESTAMP, server_default=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    __table_args__ = (
        Index('ix_guest_uuid', 'guest_uuid'),
        Index('ix_guest_ip', 'ip_address'),
    )
    
    def __repr__(self):
        identifier = self.guest_uuid or self.ip_address
        return f"<GuestSession {identifier} - {self.session_count} sessions>"


class SearchSession(Base):
    """Individual search session tracking"""
    __tablename__ = "search_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(15), nullable=True, index=True)  # NULL for guests
    guest_uuid = Column(String(36), nullable=True, index=True)  # Guest identifier
    ip_address = Column(String(45), nullable=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    search_type = Column(String(10), nullable=True)  # 'keyword' or 'url'
    search_input = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<SearchSession {self.session_id} - Completed: {self.completed}>"


class ConversationHistory(Base):
    """Store complete workflow JSON for authenticated and guest users"""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(15), nullable=True)
    guest_uuid = Column(String(36), nullable=True)
    session_id = Column(String(100), nullable=False)
    conversation_data = Column(JSON, nullable=False)  # Complete workflow JSON
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        Index('ix_conversation_phone', 'phone_number'),
        Index('ix_conversation_guest', 'guest_uuid'),
        Index('ix_conversation_session', 'session_id'),
        UniqueConstraint('phone_number', 'session_id', name='uq_conversation_phone_session'),
        UniqueConstraint('guest_uuid', 'session_id', name='uq_conversation_guest_session'),
    )

    def __repr__(self):
        owner = self.phone_number or self.guest_uuid or 'unknown'
        return f"<ConversationHistory {owner} - {self.session_id}>"
