"""
JWT token generation and validation
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Enforce JWT_SECRET_KEY in production
if ENVIRONMENT != "development":
    if not SECRET_KEY or SECRET_KEY == "dev-secret-key-change-in-production":
        raise ValueError(
            "CRITICAL: JWT_SECRET_KEY must be set in production environment. "
            "Generate a secure key using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
else:
    # Development: allow default but warn
    if not SECRET_KEY:
        SECRET_KEY = "dev-secret-key-change-in-production"
        import warnings
        warnings.warn(
            "⚠️  Using default JWT_SECRET_KEY in development. "
            "Set JWT_SECRET_KEY in .env for production!",
            UserWarning
        )

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", 30))
# Optional hardening settings
JWT_ISSUER = os.getenv("JWT_ISSUER")  # e.g., your domain
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")  # optional audience
JWT_LEEWAY_SECONDS = int(os.getenv("JWT_LEEWAY_SECONDS", 60))  # clock skew tolerance


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data to encode (should include phone_number)
        expires_delta: Custom expiration time (default: 30 days)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    })
    if JWT_ISSUER:
        to_encode.update({"iss": JWT_ISSUER})
    if JWT_AUDIENCE:
        to_encode.update({"aud": JWT_AUDIENCE})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        # Build decode kwargs with optional issuer/audience
        decode_kwargs = {
            "key": SECRET_KEY,
            "algorithms": [ALGORITHM],
            "options": {
                "require_exp": True,
                "verify_aud": bool(JWT_AUDIENCE)
            },
        }
        if JWT_ISSUER:
            decode_kwargs["issuer"] = JWT_ISSUER
        if JWT_AUDIENCE:
            decode_kwargs["audience"] = JWT_AUDIENCE

        payload = jwt.decode(token, **decode_kwargs)
        phone_number: str = payload.get("phone_number")
        token_type: str = payload.get("type")

        if phone_number is None:
            return None
        # Enforce access token type
        if token_type != "access":
            return None

        return payload
    
    except JWTError:
        return None


def get_token_expiry_time(remember_me: bool = True) -> timedelta:
    """
    Get token expiry time based on remember_me option
    
    Args:
        remember_me: If True, token lasts 30 days, else session only (1 day)
    
    Returns:
        timedelta for token expiry
    """
    if remember_me:
        return timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    else:
        return timedelta(days=1)  # Session token - 1 day
