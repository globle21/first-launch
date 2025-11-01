"""
Rate limiting for login requests to prevent abuse
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.models import LoginAttempt
from dotenv import load_dotenv

load_dotenv()

# Rate limit configuration (kept for backwards compatibility)
OTP_RATE_LIMIT_PER_HOUR = int(os.getenv("OTP_RATE_LIMIT_PER_HOUR", 3))
OTP_MAX_VERIFICATION_ATTEMPTS = int(os.getenv("OTP_MAX_VERIFICATION_ATTEMPTS", 5))


def check_otp_rate_limit(db: Session, phone_number: str) -> Tuple[bool, Optional[int]]:
    """
    Check if phone number has exceeded OTP request rate limit
    (Stub function - OTP removed, always allows requests)

    Args:
        db: Database session
        phone_number: Phone number to check

    Returns:
        Tuple of (can_request: bool, retry_after_seconds: Optional[int])
    """
    # OTP functionality removed - always allow
    return True, None


def check_verification_attempts(db: Session, phone_number: str, otp_code: str) -> bool:
    """
    Check if OTP verification attempts exceeded
    (Stub function - OTP removed, always allows)

    Args:
        db: Database session
        phone_number: Phone number
        otp_code: OTP code being verified

    Returns:
        Always True (OTP removed)
    """
    # OTP functionality removed - always allow
    return True


def increment_verification_attempts(db: Session, phone_number: str, otp_code: str):
    """
    Increment verification attempts for an OTP request
    (Stub function - OTP removed, no-op)

    Args:
        db: Database session
        phone_number: Phone number
        otp_code: OTP code
    """
    # OTP functionality removed - no-op
    pass


def check_login_rate_limit(db: Session, phone_number: str, max_attempts: int = 5, window_seconds: int = 3600) -> Tuple[bool, Optional[int]]:
    """
    Check if phone number has exceeded login attempt rate limit

    Uses LoginAttempt table to track login attempts for phone-only authentication.

    Args:
        db: Database session
        phone_number: Phone number to check
        max_attempts: Maximum login attempts allowed (default: 5)
        window_seconds: Time window in seconds (default: 3600 = 1 hour)

    Returns:
        Tuple of (can_login: bool, retry_after_seconds: Optional[int])
    """
    # Get timestamp for the window
    window_start = datetime.utcnow() - timedelta(seconds=window_seconds)

    # Count login attempts in the time window
    recent_attempts = db.query(LoginAttempt).filter(
        and_(
            LoginAttempt.phone_number == phone_number,
            LoginAttempt.attempt_type == "login",
            LoginAttempt.created_at >= window_start
        )
    ).count()

    if recent_attempts >= max_attempts:
        # Get the oldest attempt in the window
        oldest_attempt = db.query(LoginAttempt).filter(
            and_(
                LoginAttempt.phone_number == phone_number,
                LoginAttempt.attempt_type == "login",
                LoginAttempt.created_at >= window_start
            )
        ).order_by(LoginAttempt.created_at.asc()).first()

        if oldest_attempt:
            # Calculate when the oldest attempt will expire from the window
            expires_at = oldest_attempt.created_at + timedelta(seconds=window_seconds)
            retry_after = int((expires_at - datetime.utcnow()).total_seconds())
            return False, max(retry_after, 60)  # At least 60 seconds

        return False, window_seconds  # Default to full window

    # Record this login attempt
    login_track = LoginAttempt(
        phone_number=phone_number,
        attempt_type="login",
    )
    db.add(login_track)
    db.commit()

    return True, None
