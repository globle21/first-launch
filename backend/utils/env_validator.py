"""
Environment variable validation on startup
Ensures all required and recommended environment variables are set correctly
"""
import os
import logging
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class EnvVarConfig:
    """Configuration for an environment variable"""
    def __init__(
        self,
        name: str,
        required: bool = False,
        default: Optional[str] = None,
        validator: Optional[callable] = None,
        description: str = ""
    ):
        self.name = name
        self.required = required
        self.default = default
        self.validator = validator
        self.description = description


def validate_env_vars(environment: str = None) -> Tuple[bool, List[str]]:
    """
    Validate environment variables based on environment (development/production)
    
    Args:
        environment: "development" or "production" (defaults to ENVIRONMENT env var)
    
    Returns:
        Tuple of (is_valid: bool, error_messages: List[str])
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()
    
    errors = []
    warnings = []
    
    # Common configurations for all environments
    env_configs = [
        EnvVarConfig(
            name="DATABASE_URL",
            required=True,
            description="PostgreSQL database connection string"
        ),
        EnvVarConfig(
            name="JWT_SECRET_KEY",
            required=(environment == "production"),
            description="Secret key for JWT token signing"
        ),
        EnvVarConfig(
            name="ENVIRONMENT",
            required=False,
            default="development",
            description="Application environment: 'development' or 'production'"
        ),
        EnvVarConfig(
            name="GUEST_SESSION_LIMIT",
            required=False,
            default="2",
            validator=lambda v: v.isdigit() and int(v) > 0,
            description="Maximum number of free searches for guest users"
        ),
    ]
    
    # Production-specific configurations
    if environment == "production":
        env_configs.extend([
            EnvVarConfig(
                name="CORS_ALLOWED_ORIGINS",
                required=True,
                description="Comma-separated list of allowed CORS origins"
            ),
            EnvVarConfig(
                name="JWT_ISSUER",
                required=False,
                description="JWT issuer claim (recommended in production)"
            ),
            EnvVarConfig(
                name="JWT_AUDIENCE",
                required=False,
                description="JWT audience claim (optional)"
            ),
            EnvVarConfig(
                name="JWT_LEEWAY_SECONDS",
                required=False,
                default="60",
                validator=lambda v: v.isdigit() and int(v) >= 0,
                description="JWT clock-skew leeway in seconds"
            ),
            EnvVarConfig(
                name="DB_POOL_SIZE",
                required=False,
                default="10",
                validator=lambda v: v.isdigit() and int(v) > 0,
                description="Database connection pool size"
            ),
            EnvVarConfig(
                name="DB_MAX_OVERFLOW",
                required=False,
                default="20",
                validator=lambda v: v.isdigit() and int(v) >= 0,
                description="Maximum database connection pool overflow"
            ),
        ])
    
    # Validate each environment variable
    for config in env_configs:
        value = os.getenv(config.name, config.default)
        
        # Check if required variable is missing
        if config.required and not value:
            errors.append(
                f"Required environment variable '{config.name}' is not set. "
                f"{config.description}"
            )
            continue
        
        # If variable has a value, validate it
        if value and config.validator:
            try:
                if not config.validator(value):
                    errors.append(
                        f"Environment variable '{config.name}' has invalid value. "
                        f"{config.description}"
                    )
            except Exception as e:
                errors.append(
                    f"Environment variable '{config.name}' validation failed: {e}. "
                    f"{config.description}"
                )
    
    # Additional validation checks
    if environment == "production":
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if jwt_secret and jwt_secret == "dev-secret-key-change-in-production":
            errors.append(
                "JWT_SECRET_KEY is set to default development value. "
                "Generate a secure key for production!"
            )
        
        cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
        if cors_origins and "*" in cors_origins:
            warnings.append(
                "CORS_ALLOWED_ORIGINS contains '*'. This is insecure for production. "
                "Use specific domain names."
            )
    
    # Log results
    if errors:
        logger.error(f"Environment validation failed with {len(errors)} error(s):")
        for error in errors:
            logger.error(f"  ❌ {error}")
    
    if warnings:
        logger.warning(f"Environment validation found {len(warnings)} warning(s):")
        for warning in warnings:
            logger.warning(f"  ⚠️  {warning}")
    
    if not errors and not warnings:
        logger.info("✅ Environment variable validation passed")
    elif not errors:
        logger.info("✅ Environment variable validation passed (with warnings)")
    
    return len(errors) == 0, errors + warnings


def print_env_summary():
    """Print a summary of current environment configuration"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    logger.info("=" * 60)
    logger.info("Environment Configuration Summary")
    logger.info("=" * 60)
    logger.info(f"Environment: {environment}")
    logger.info(f"DATABASE_URL: {'✅ Set' if os.getenv('DATABASE_URL') else '❌ Not set'}")
    logger.info(f"JWT_SECRET_KEY: {'✅ Set' if os.getenv('JWT_SECRET_KEY') else '❌ Not set'}")
    
    if environment == "production":
        logger.info(f"CORS_ALLOWED_ORIGINS: {'✅ Set' if os.getenv('CORS_ALLOWED_ORIGINS') else '❌ Not set'}")
    
    logger.info(f"GUEST_SESSION_LIMIT: {os.getenv('GUEST_SESSION_LIMIT', '2')}")
    logger.info("=" * 60)

