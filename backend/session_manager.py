"""
Session Manager for Workflow State
In-memory storage for workflow sessions with user confirmations
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import threading


@dataclass
class WorkflowSession:
    """Represents a workflow session"""
    session_id: str
    input_type: str  # "keyword" or "url"
    user_input: str
    created_at: datetime
    last_updated: datetime

    # Workflow state
    current_stage: str = "initializing"
    status: str = "running"  # running, waiting_confirmation, completed, failed

    # State data (mirrors WorkflowState)
    state_data: Dict[str, Any] = field(default_factory=dict)

    # Real-time updates
    progress_logs: List[Dict[str, Any]] = field(default_factory=list)

    # User confirmation tracking
    needs_product_confirmation: bool = False
    product_candidates: List[Dict] = field(default_factory=list)
    confirmed_product_index: Optional[int] = None

    needs_variant_confirmation: bool = False
    variant_candidates: List[Dict] = field(default_factory=list)
    confirmed_variant_index: Optional[int] = None

    needs_url_extraction_confirmation: bool = False
    extracted_details: Optional[Dict] = None
    url_extraction_confirmed: bool = False

    # Results
    final_results: Optional[List[Dict]] = None
    error_message: Optional[str] = None

    # Cleanup management
    marked_for_cleanup: bool = False
    cleanup_after: Optional[datetime] = None


class SessionManager:
    """Manages workflow sessions in-memory"""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, WorkflowSession] = {}
        self.lock = threading.Lock()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(self, input_type: str, user_input: str) -> str:
        """Create a new workflow session"""
        session_id = str(uuid.uuid4())
        
        session = WorkflowSession(
            session_id=session_id,
            input_type=input_type,
            user_input=user_input,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        with self.lock:
            self.sessions[session_id] = session
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        """Get session by ID"""
        with self.lock:
            return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs):
        """Update session fields"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.last_updated = datetime.now()
    
    def add_progress_log(self, session_id: str, log_entry: Dict[str, Any]):
        """Add a progress log entry"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.progress_logs.append({
                    **log_entry,
                    "timestamp": datetime.now().isoformat()
                })
                session.last_updated = datetime.now()
    
    def set_product_confirmation_needed(
        self, 
        session_id: str, 
        product_candidates: List[Dict]
    ):
        """Set session to wait for product confirmation"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = "waiting_confirmation"
                session.needs_product_confirmation = True
                session.product_candidates = product_candidates
                session.current_stage = "product_confirmation"
                session.last_updated = datetime.now()
    
    def confirm_product(self, session_id: str, product_index: int) -> bool:
        """Confirm product selection"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session and session.needs_product_confirmation:
                if 0 <= product_index < len(session.product_candidates):
                    session.confirmed_product_index = product_index
                    session.needs_product_confirmation = False
                    session.status = "running"
                    session.last_updated = datetime.now()
                    return True
        return False
    
    def set_variant_confirmation_needed(
        self, 
        session_id: str, 
        variant_candidates: List[Dict]
    ):
        """Set session to wait for variant confirmation"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = "waiting_confirmation"
                session.needs_variant_confirmation = True
                session.variant_candidates = variant_candidates
                session.current_stage = "variant_confirmation"
                session.last_updated = datetime.now()
    
    def confirm_variant(self, session_id: str, variant_index: int) -> bool:
        """Confirm variant selection"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session and session.needs_variant_confirmation:
                if 0 <= variant_index < len(session.variant_candidates):
                    session.confirmed_variant_index = variant_index
                    session.needs_variant_confirmation = False
                    session.status = "running"
                    session.last_updated = datetime.now()
                    return True
        return False
    
    def set_url_extraction_confirmation_needed(
        self, 
        session_id: str, 
        extracted_details: Dict
    ):
        """Set session to wait for URL extraction confirmation"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = "waiting_confirmation"
                session.needs_url_extraction_confirmation = True
                session.extracted_details = extracted_details
                session.current_stage = "url_extraction_confirmation"
                session.last_updated = datetime.now()
    
    def confirm_url_extraction(self, session_id: str, confirmed: bool) -> bool:
        """Confirm or reject URL extraction"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session and session.needs_url_extraction_confirmation:
                session.url_extraction_confirmed = confirmed
                session.needs_url_extraction_confirmation = False
                
                if confirmed:
                    session.status = "running"
                else:
                    session.status = "failed"
                    session.error_message = "User rejected URL extraction"
                
                session.last_updated = datetime.now()
                return True
        return False
    
    def set_completed(self, session_id: str, final_results: List[Dict]):
        """Mark session as completed with results"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = "completed"
                session.current_stage = "complete"
                session.final_results = final_results
                session.last_updated = datetime.now()
    
    def set_failed(self, session_id: str, error_message: str):
        """Mark session as failed"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = "failed"
                session.error_message = error_message
                session.last_updated = datetime.now()

    def mark_for_cleanup(self, session_id: str, cleanup_delay_minutes: int = 10):
        """
        Mark session for cleanup after specified delay

        Args:
            session_id: Session ID to mark
            cleanup_delay_minutes: Minutes to wait before cleanup (default: 10)
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.marked_for_cleanup = True
                session.cleanup_after = datetime.now() + timedelta(minutes=cleanup_delay_minutes)
                print(f"🧹 Session {session_id[:8]}... marked for cleanup at {session.cleanup_after.strftime('%H:%M:%S')}")

    def cleanup_old_sessions(self):
        """
        Remove old sessions from memory based on cleanup rules:

        1. Sessions marked_for_cleanup: Remove after cleanup_after time (typically 10 minutes)
        2. Running sessions: Remove if inactive for session_timeout (30 minutes)
        3. Waiting sessions: Remove if inactive for session_timeout (30 minutes)
        """
        with self.lock:
            now = datetime.now()
            sessions_to_remove = []

            for sid, session in self.sessions.items():
                # Rule 1: Marked for cleanup - remove after cleanup_after time
                if session.marked_for_cleanup and session.cleanup_after:
                    if now >= session.cleanup_after:
                        sessions_to_remove.append((sid, "marked_cleanup"))
                        continue

                # Rule 2: Running/waiting sessions - remove if inactive for timeout
                if session.status in ["running", "waiting_confirmation"]:
                    if now - session.last_updated > self.session_timeout:
                        sessions_to_remove.append((sid, "timeout"))
                        continue

            # Remove identified sessions
            for sid, reason in sessions_to_remove:
                del self.sessions[sid]
                if reason == "marked_cleanup":
                    print(f"🧹 Cleaned up session {sid[:8]}... (scheduled cleanup)")
                elif reason == "timeout":
                    print(f"🧹 Cleaned up session {sid[:8]}... (timeout - inactive for {self.session_timeout.total_seconds()/60:.0f} minutes)")

            if sessions_to_remove:
                print(f"📊 Active sessions: {len(self.sessions)}")
    
    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        with self.lock:
            return len(self.sessions)

    def get_all_sessions(self) -> Dict[str, 'WorkflowSession']:
        """Get a copy of all active sessions"""
        with self.lock:
            return self.sessions.copy()

# Global session manager instance
session_manager = SessionManager()
