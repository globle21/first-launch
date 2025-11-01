"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class SendOTPRequest(BaseModel):
    """Request to send OTP"""
    phone_number: str = Field(..., description="Phone number with country code, e.g., +919876543210")
    
    @validator('phone_number')
    def validate_full_phone(cls, v):
        # Must start with + and have 11-15 digits total
        if not re.match(r'^\+\d{11,15}$', v):
            raise ValueError('Invalid phone number format. Must be +[country_code][number]')
        return v


class LoginPhoneRequest(BaseModel):
    """Request to login with phone number (no OTP required)"""
    phone_number: str = Field(..., description="Phone number with country code in E.164 format, e.g., +919876543210")
    
    @validator('phone_number')
    def validate_full_phone(cls, v):
        # Must start with + and have 11-15 digits total (E.164 format)
        if not re.match(r'^\+\d{11,15}$', v):
            raise ValueError('Invalid phone number format. Must be E.164 format: +[country_code][number] (e.g., +919876543210)')
        return v


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP"""
    phone_number: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    remember_me: bool = Field(default=True, description="Remember user for 30 days")
    
    @validator('otp_code')
    def validate_otp(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('OTP must be 6 digits')
        return v


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    phone_number: str


class UserResponse(BaseModel):
    """User information response"""
    phone_number: str
    country_code: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    total_sessions: int
    
    class Config:
        from_attributes = True


class SessionLimitCheck(BaseModel):
    """Response for session limit check"""
    can_search: bool
    sessions_used: int
    sessions_remaining: int
    requires_auth: bool
    message: str


class OTPStatusResponse(BaseModel):
    """OTP send status response"""
    success: bool
    message: str
    retry_after: Optional[int] = None  # Seconds until can retry


class TrackSessionRequest(BaseModel):
    """Request to track a search session"""
    session_id: str = Field(..., min_length=1, max_length=100, description="Unique session identifier")
    search_type: str = Field(..., description="Type of search: 'keyword' or 'url'")
    search_input: str = Field(..., min_length=1, description="The search query or URL")
    guest_uuid: Optional[str] = Field(None, description="Guest UUID for guest sessions")
    
    @validator('search_type')
    def validate_search_type(cls, v):
        allowed_types = ['keyword', 'url']
        if v not in allowed_types:
            raise ValueError(f'search_type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('search_input')
    def validate_search_input(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('search_input cannot be empty')
        if len(v) > 5000:  # Reasonable max length
            raise ValueError('search_input exceeds maximum length of 5000 characters')
        return v.strip()
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('session_id cannot be empty')
        return v.strip()
