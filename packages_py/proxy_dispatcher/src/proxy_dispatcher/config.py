"""
Environment detection functions.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_app_env(default: str = "dev") -> str:
    """Get the current application environment."""
    env = os.getenv("APP_ENV", default)
    logger.debug(f"Resolved APP_ENV: {env}")
    return env

def is_dev() -> bool:
    """Check if running in DEV environment."""
    return get_app_env().lower() == "dev"

def is_prod() -> bool:
    """Check if running in PROD environment."""
    return get_app_env().lower() == "prod"

def is_ssl_verify_disabled_by_env() -> bool:
    """Check if SSL verification is disabled by environment variables."""
    # Node.js compatibility
    if os.getenv("NODE_TLS_REJECT_UNAUTHORIZED") == "0":
        return True
    
    # Python convention
    if os.getenv("SSL_CERT_VERIFY") == "0":
        return True
        
    return False
