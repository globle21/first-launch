"""
Rate limiting for OTP requests to prevent abuse
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

from auth.models import OTPRequest
from dotenv import load_dotenv

load_dotenv()

# Rate limit configuration
OTP_RATE_LIMIT_PER_HOUR = int(os.getenv("OTP_RATE_LIMIT_PER_HOUR", 3))
OTP_MAX_VERIFICATION_ATTEMPTS = int(os.getenv("OTP_MAX_VERIFICATION_ATTEMPTS", 5))


def check_otp_rate_limit(db: Session, phone_number: str) -> Tuple[bool, Optional[int]]:
    """
    Check if phone number has exceeded OTP request rate limit
    
    Args:
        db: Database session
        phone_number: Phone number to check
    
    Returns:
        Tuple of (can_request: bool, retry_after_seconds: Optional[int])
    """
    # Get timestamp for 1 hour ago
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Count OTP requests in the last hour
    recent_requests = db.query(OTPRequest).filter(
        and_(
            OTPRequest.phone_number == phone_number,
            OTPRequest.created_at >= one_hour_ago
        )
    ).count()
    
    if recent_requests >= OTP_RATE_LIMIT_PER_HOUR:
        # Get the oldest request in the window
        oldest_request = db.query(OTPRequest).filter(
            and_(
                OTPRequest.phone_number == phone_number,
                OTPRequest.created_at >= one_hour_ago
            )
        ).order_by(OTPRequest.created_at.asc()).first()
        
        if oldest_request:
            # Calculate when the oldest request will expire from the 1-hour window
            expires_at = oldest_request.created_at + timedelta(hours=1)
            retry_after = int((expires_at - datetime.utcnow()).total_seconds())
            return False, max(retry_after, 60)  # At least 60 seconds
        
        return False, 3600  # Default to 1 hour
    
    return True, None


def check_verification_attempts(db: Session, phone_number: str, otp_code: str) -> bool:
    """
    Check if OTP verification attempts exceeded
    
    Args:
        db: Database session
        phone_number: Phone number
        otp_code: OTP code being verified
    
    Returns:
        True if can attempt verification, False if exceeded limit
    """
    # Find the OTP request
    otp_request = db.query(OTPRequest).filter(
        and_(
            OTPRequest.phone_number == phone_number,
            OTPRequest.otp_code == otp_code,
            OTPRequest.is_verified == False
        )
    ).order_by(OTPRequest.created_at.desc()).first()
    
    if not otp_request:
        return True  # No request found, allow attempt
    
    # Check if exceeded max attempts
    if otp_request.verification_attempts >= OTP_MAX_VERIFICATION_ATTEMPTS:
        return False
    
    return True


def increment_verification_attempts(db: Session, phone_number: str, otp_code: str):
    """
    Increment verification attempts for an OTP request
    
    Args:
        db: Database session
        phone_number: Phone number
        otp_code: OTP code
    """
    otp_request = db.query(OTPRequest).filter(
        and_(
            OTPRequest.phone_number == phone_number,
            OTPRequest.otp_code == otp_code,
            OTPRequest.is_verified == False
        )
    ).order_by(OTPRequest.created_at.desc()).first()
    
    if otp_request:
        otp_request.verification_attempts += 1
        db.commit()


def check_login_rate_limit(db: Session, phone_number: str, max_attempts: int = 5, window_seconds: int = 3600) -> Tuple[bool, Optional[int]]:
    """
    Check if phone number has exceeded login attempt rate limit
    
    This uses OTPRequest table to track login attempts (repurposing the table)
    since we track by phone_number and created_at.
    
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
    
    # Count login attempts (using OTPRequest table entries for this phone)
    # We'll count any OTPRequest entry as a login attempt proxy
    recent_attempts = db.query(OTPRequest).filter(
        and_(
            OTPRequest.phone_number == phone_number,
            OTPRequest.created_at >= window_start
        )
    ).count()
    
    if recent_attempts >= max_attempts:
        # Get the oldest attempt in the window
        oldest_attempt = db.query(OTPRequest).filter(
            and_(
                OTPRequest.phone_number == phone_number,
                OTPRequest.created_at >= window_start
            )
        ).order_by(OTPRequest.created_at.asc()).first()
        
        if oldest_attempt:
            # Calculate when the oldest attempt will expire from the window
            expires_at = oldest_attempt.created_at + timedelta(seconds=window_seconds)
            retry_after = int((expires_at - datetime.utcnow()).total_seconds())
            return False, max(retry_after, 60)  # At least 60 seconds
        
        return False, window_seconds  # Default to full window
    
    # Record this login attempt (create a dummy OTPRequest entry for tracking)
    # In production, consider a dedicated LoginAttempt model
    login_track = OTPRequest(
        phone_number=phone_number,
        otp_code="LOGIN_ATTEMPT",  # Dummy code to track login
        expires_at=datetime.utcnow() + timedelta(hours=1),
        is_verified=False,
        verification_attempts=0
    )
    db.add(login_track)
    db.commit()
    
    return True, None
