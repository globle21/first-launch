"""
OTP service - Mock mode for development
"""
import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Configuration
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", 5))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


def generate_otp(length: int = 6) -> str:
    """
    Generate a random OTP code
    
    Args:
        length: Length of OTP (default: 6)
    
    Returns:
        Numeric OTP string
    """
    return ''.join(random.choices(string.digits, k=length))


def get_otp_expiry_time() -> datetime:
    """
    Get OTP expiry timestamp
    
    Returns:
        Datetime when OTP expires (current time + OTP_EXPIRY_MINUTES)
    """
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)


async def send_otp_mock(phone_number: str, otp_code: str) -> Tuple[bool, Optional[str]]:
    """
    Mock OTP sending for development/testing
    Just prints OTP to console instead of sending SMS
    
    USE ONLY IN DEVELOPMENT - NEVER IN PRODUCTION
    """
    print("\n" + "=" * 60)
    print("🧪 DEVELOPMENT MODE - OTP NOT SENT VIA SMS")
    print("=" * 60)
    print(f"📱 Phone: {phone_number}")
    print(f"🔢 OTP Code: {otp_code}")
    print(f"⏰ Valid for: {OTP_EXPIRY_MINUTES} minutes")
    print("=" * 60 + "\n")
    return True, None


# Twilio integration for production
async def send_otp_twilio(phone_number: str, otp_code: str) -> Tuple[bool, Optional[str]]:
    """
    Send OTP via Twilio SMS (for production)

    Args:
        phone_number: Phone number with country code (e.g., +919876543210)
        otp_code: 6-digit OTP code to send

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        # Import Twilio (will fail gracefully if not installed)
        from twilio.rest import Client

        # Get Twilio credentials from environment
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

        # Validate credentials are configured
        if not all([account_sid, auth_token, twilio_number]):
            error_msg = "Twilio credentials not configured in .env file"
            print(f"❌ {error_msg}")
            print("   Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")
            return False, error_msg

        # Initialize Twilio client
        client = Client(account_sid, auth_token)

        # Compose SMS message
        message_body = (
            f"Your Globle Club verification code is: {otp_code}\n"
            f"Valid for {OTP_EXPIRY_MINUTES} minutes.\n"
            f"Do not share this code with anyone."
        )

        # Send SMS via Twilio
        message = client.messages.create(
            body=message_body,
            from_=twilio_number,
            to=phone_number
        )

        print(f"✅ OTP sent via Twilio to {phone_number}")
        print(f"   Message SID: {message.sid}")
        print(f"   Status: {message.status}")

        return True, None

    except ImportError:
        error_msg = "Twilio package not installed. Run: pip install twilio"
        print(f"❌ {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Twilio error: {str(e)}"
        print(f"❌ Failed to send OTP via Twilio: {error_msg}")
        return False, error_msg


# Choose which function to use based on environment
if ENVIRONMENT == "production":
    send_otp = send_otp_twilio
else:
    send_otp = send_otp_mock  # Use mock for development
