"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from auth import models, schemas
from auth.otp_service import generate_otp, get_otp_expiry_time, send_otp
from auth.rate_limiter import (
    check_otp_rate_limit,
    check_verification_attempts,
    increment_verification_attempts,
    check_login_rate_limit
)
from auth.jwt_handler import create_access_token, get_token_expiry_time
from auth.dependencies import get_current_user, require_auth, get_client_ip

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

GUEST_SESSION_LIMIT = int(os.getenv("GUEST_SESSION_LIMIT", 2))


@router.post("/send-otp", response_model=schemas.OTPStatusResponse)
async def send_otp_endpoint(
    request_data: schemas.SendOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Send OTP to phone number
    
    Steps:
    1. Check rate limit (3 requests per hour)
    2. Generate OTP code
    3. Store in database with expiry
    4. Send via mock service (prints to console)
    """
    phone_number = request_data.phone_number
    
    # Check rate limit
    can_request, retry_after = check_otp_rate_limit(db, phone_number)
    
    if not can_request:
        return schemas.OTPStatusResponse(
            success=False,
            message=f"Too many OTP requests. Please try again in {retry_after // 60} minutes.",
            retry_after=retry_after
        )
    
    # Generate OTP
    otp_code = generate_otp()
    expires_at = get_otp_expiry_time()
    
    # Store OTP in database
    otp_request = models.OTPRequest(
        phone_number=phone_number,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_request)
    db.commit()
    
    # Send OTP (mock mode - prints to console)
    success, error = await send_otp(phone_number, otp_code)
    
    if not success:
        return schemas.OTPStatusResponse(
            success=False,
            message=f"Failed to send OTP: {error}"
        )
    
    return schemas.OTPStatusResponse(
        success=True,
        message="OTP sent successfully. Check your console/terminal for the code."
    )


@router.post("/verify-otp", response_model=schemas.TokenResponse)
async def verify_otp_endpoint(
    request_data: schemas.VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and return JWT token
    
    Steps:
    1. Find OTP request in database
    2. Check if expired
    3. Check if verification attempts exceeded
    4. Verify OTP code matches
    5. Create or get user
    6. Generate JWT token
    7. Mark OTP as verified
    """
    phone_number = request_data.phone_number
    otp_code = request_data.otp_code
    remember_me = request_data.remember_me
    
    # Check verification attempts
    if not check_verification_attempts(db, phone_number, otp_code):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please request a new OTP."
        )
    
    # Find the most recent unverified OTP request
    otp_request = db.query(models.OTPRequest).filter(
        models.OTPRequest.phone_number == phone_number,
        models.OTPRequest.is_verified == False
    ).order_by(models.OTPRequest.created_at.desc()).first()
    
    if not otp_request:
        increment_verification_attempts(db, phone_number, otp_code)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OTP request found. Please request a new OTP."
        )
    
    # Check if expired
    if datetime.utcnow() > otp_request.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )
    
    # Verify OTP code
    if otp_request.otp_code != otp_code:
        increment_verification_attempts(db, phone_number, otp_code)
        remaining_attempts = 5 - (otp_request.verification_attempts + 1)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP code. {remaining_attempts} attempts remaining."
        )
    
    # Mark OTP as verified
    otp_request.is_verified = True
    db.commit()
    
    # Create or get user
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()
    
    if not user:
        # Extract country code
        country_code = phone_number[:3] if phone_number.startswith('+') else '+91'
        
        user = models.User(
            phone_number=phone_number,
            country_code=country_code,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # Generate JWT token
    token_expiry = get_token_expiry_time(remember_me)
    access_token = create_access_token(
        data={"phone_number": phone_number},
        expires_delta=token_expiry
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(token_expiry.total_seconds()),
        phone_number=phone_number
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    current_user: models.User = Depends(require_auth)
):
    """
    Get current authenticated user information
    """
    return current_user


@router.post("/login-phone", response_model=schemas.TokenResponse)
async def login_phone(
    request_data: schemas.LoginPhoneRequest,
    db: Session = Depends(get_db)
):
    """
    Login with phone number only (no OTP required)
    
    Steps:
    1. Check rate limit (5 login attempts per hour per phone number)
    2. Create or get user
    3. Update last login
    4. Generate JWT token
    """
    phone_number = request_data.phone_number
    
    # Rate limiting: 5 login attempts per hour per phone number
    can_login, retry_after = check_login_rate_limit(db, phone_number, max_attempts=5, window_seconds=3600)
    
    if not can_login:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {retry_after // 60} minutes."
        )
    
    # Create or get user
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()
    
    if not user:
        # Extract country code (first 3 chars after +)
        country_code = phone_number[:4] if phone_number.startswith('+') and len(phone_number) > 3 else '+91'
        
        user = models.User(
            phone_number=phone_number,
            country_code=country_code,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate JWT token (30 days expiry by default)
    token_expiry = get_token_expiry_time(remember_me=True)
    access_token = create_access_token(
        data={"phone_number": phone_number},
        expires_delta=token_expiry
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(token_expiry.total_seconds()),
        phone_number=phone_number
    )


@router.post("/logout")
async def logout(
    current_user: models.User = Depends(require_auth)
):
    """
    Logout user (client should delete token from localStorage)
    """
    return {"message": "Logged out successfully"}


@router.get("/check-session-limit", response_model=schemas.SessionLimitCheck)
async def check_session_limit(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user/guest can perform another search session
    
    Returns:
        - Authenticated users: Always can search
        - Guest users: Check if under limit (tracks by guest_uuid first, then IP fallback)
    """
    # Authenticated users have unlimited searches
    if current_user:
        return schemas.SessionLimitCheck(
            can_search=True,
            sessions_used=current_user.total_sessions,
            sessions_remaining=-1,  # Unlimited
            requires_auth=False,
            message="Authenticated user - unlimited searches"
        )
    
    # Guest user - get guest_uuid from header first
    guest_uuid = request.headers.get("X-Guest-Id")
    client_ip = get_client_ip(request)
    
    # Try to find guest session by UUID first (most accurate)
    guest_session = None
    if guest_uuid:
        guest_session = db.query(models.GuestSession).filter(
            models.GuestSession.guest_uuid == guest_uuid
        ).first()
    
    # Fallback to IP-based tracking if no UUID match
    if not guest_session:
        guest_session = db.query(models.GuestSession).filter(
            models.GuestSession.ip_address == client_ip,
            models.GuestSession.guest_uuid.is_(None)  # Only IP-based sessions without UUID
        ).first()
    
    if not guest_session:
        # First time visitor
        return schemas.SessionLimitCheck(
            can_search=True,
            sessions_used=0,
            sessions_remaining=GUEST_SESSION_LIMIT,
            requires_auth=False,
            message=f"Welcome! You have {GUEST_SESSION_LIMIT} free searches."
        )
    
    sessions_used = guest_session.session_count
    sessions_remaining = GUEST_SESSION_LIMIT - sessions_used
    
    if sessions_used >= GUEST_SESSION_LIMIT:
        # Exceeded limit
        return schemas.SessionLimitCheck(
            can_search=False,
            sessions_used=sessions_used,
            sessions_remaining=0,
            requires_auth=True,
            message=f"You've used all {GUEST_SESSION_LIMIT} free searches. Please sign in to continue."
        )
    
    # Still have sessions remaining
    return schemas.SessionLimitCheck(
        can_search=True,
        sessions_used=sessions_used,
        sessions_remaining=sessions_remaining,
        requires_auth=False,
        message=f"You have {sessions_remaining} free search{'es' if sessions_remaining != 1 else ''} remaining."
    )


@router.post("/track-session")
async def track_session_start(
    request: Request,
    request_data: Optional[schemas.TrackSessionRequest] = None,
    session_id: Optional[str] = None,
    search_type: Optional[str] = None,
    search_input: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Track when a search session starts
    Called from frontend when user starts a new search
    
    Accepts data from JSON body (preferred) or query parameters (fallback)
    """
    client_ip = get_client_ip(request)
    
    # Get guest_uuid from header if not in body
    guest_uuid_header = request.headers.get("X-Guest-Id")
    
    # Parse request data - prefer JSON body, fallback to query params
    if request_data:
        # JSON body provided
        session_id = request_data.session_id
        search_type = request_data.search_type
        search_input = request_data.search_input
        guest_uuid = request_data.guest_uuid or guest_uuid_header
    else:
        # Fallback to query parameters (for backward compatibility)
        if not session_id or not search_type or not search_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters: session_id, search_type, and search_input are required"
            )
        guest_uuid = guest_uuid_header
        
        # Validate search_type manually for query params
        if search_type not in ['keyword', 'url']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="search_type must be 'keyword' or 'url'"
            )
        
        # Validate search_input
        if not search_input or len(search_input.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="search_input cannot be empty"
            )
        search_input = search_input.strip()
    
    # Create search session record
    search_session = models.SearchSession(
        phone_number=current_user.phone_number if current_user else None,
        guest_uuid=guest_uuid if not current_user else None,
        ip_address=client_ip,
        session_id=session_id,
        search_type=search_type,
        search_input=search_input,
        completed=False
    )
    db.add(search_session)
    
    # Update counters
    if current_user:
        # Authenticated user
        current_user.total_sessions += 1
    else:
        # Guest user - track by guest_uuid if available, otherwise by IP
        guest_session = None
        
        # Priority 1: Try to find by guest_uuid (most accurate per-user tracking)
        if guest_uuid:
            guest_session = db.query(models.GuestSession).filter(
                models.GuestSession.guest_uuid == guest_uuid
            ).first()
            
            if guest_session:
                # Update existing UUID-based session
                guest_session.session_count += 1
                guest_session.last_session_at = datetime.utcnow()
                # Update IP if changed (user moved networks)
                if guest_session.ip_address != client_ip:
                    guest_session.ip_address = client_ip
            else:
                # Create new UUID-based session
                guest_session = models.GuestSession(
                    guest_uuid=guest_uuid,
                    ip_address=client_ip,
                    user_agent=request.headers.get("User-Agent", ""),
                    session_count=1
                )
                db.add(guest_session)
        
        # Priority 2: Fallback to IP-based tracking (if no UUID provided)
        if not guest_session:
            guest_session = db.query(models.GuestSession).filter(
                models.GuestSession.ip_address == client_ip,
                models.GuestSession.guest_uuid.is_(None)  # Only IP-based sessions
            ).first()
            
            if guest_session:
                guest_session.session_count += 1
                guest_session.last_session_at = datetime.utcnow()
            else:
                # Create new IP-based session
                guest_session = models.GuestSession(
                    guest_uuid=None,  # No UUID available
                    ip_address=client_ip,
                    user_agent=request.headers.get("User-Agent", ""),
                    session_count=1
                )
                db.add(guest_session)
    
    db.commit()
    
    return {"message": "Session tracked", "session_id": session_id}


@router.post("/complete-session")
async def complete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a search session as completed
    Called from frontend when search workflow finishes (results displayed)
    """
    search_session = db.query(models.SearchSession).filter(
        models.SearchSession.session_id == session_id
    ).first()
    
    if search_session:
        search_session.completed = True
        search_session.completed_at = datetime.utcnow()
        db.commit()
    
    return {"message": "Session marked as complete"}
