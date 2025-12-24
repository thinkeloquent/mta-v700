"""
Auth handler utilities for fetch_client.
"""
import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

from ..types import RequestContext
from ..config import AuthConfig

logger = logging.getLogger(__name__)
LOG_PREFIX = f"[AUTH:{__file__}]"


def _mask_value(val: Optional[str]) -> str:
    """Mask sensitive value for logging, showing first 10 chars."""
    if not val:
        return "<empty>"
    if len(val) <= 10:
        return "*" * len(val)
    return val[:10] + "*" * (len(val) - 10)


class AuthHandler(ABC):
    """Auth handler interface."""

    @abstractmethod
    def get_header(self, context: RequestContext) -> Optional[Dict[str, str]]:
        """Get auth header for request."""
        ...


class BearerAuthHandler(AuthHandler):
    """Bearer token auth handler."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        get_api_key_for_request: Optional[
            Callable[[RequestContext], Optional[str]]
        ] = None,
    ):
        self._api_key = api_key
        self._get_api_key_for_request = get_api_key_for_request

    def get_header(self, context: RequestContext) -> Optional[Dict[str, str]]:
        """Get bearer auth header."""
        key = None
        if self._get_api_key_for_request:
            key = self._get_api_key_for_request(context)
        if not key:
            key = self._api_key
        if not key:
            return None
        header = {"Authorization": f"Bearer {key}"}
        logger.debug(
            f"{LOG_PREFIX} BearerAuthHandler.get_header: api_key={_mask_value(key)} -> "
            f"Authorization={_mask_value(header['Authorization'])}"
        )
        return header


class XApiKeyAuthHandler(AuthHandler):
    """X-API-Key auth handler."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        get_api_key_for_request: Optional[
            Callable[[RequestContext], Optional[str]]
        ] = None,
    ):
        self._api_key = api_key
        self._get_api_key_for_request = get_api_key_for_request

    def get_header(self, context: RequestContext) -> Optional[Dict[str, str]]:
        """Get x-api-key auth header."""
        key = None
        if self._get_api_key_for_request:
            key = self._get_api_key_for_request(context)
        if not key:
            key = self._api_key
        if not key:
            return None
        logger.debug(f"{LOG_PREFIX} XApiKeyAuthHandler.get_header: api_key={_mask_value(key)}")
        return {"x-api-key": key}


class CustomAuthHandler(AuthHandler):
    """Custom header auth handler."""

    def __init__(
        self,
        header_name: str,
        api_key: Optional[str] = None,
        get_api_key_for_request: Optional[
            Callable[[RequestContext], Optional[str]]
        ] = None,
    ):
        self._header_name = header_name
        self._api_key = api_key
        self._get_api_key_for_request = get_api_key_for_request

    def get_header(self, context: RequestContext) -> Optional[Dict[str, str]]:
        """Get custom auth header."""
        key = None
        if self._get_api_key_for_request:
            key = self._get_api_key_for_request(context)
        if not key:
            key = self._api_key
        if not key:
            return None
        logger.debug(
            f"{LOG_PREFIX} CustomAuthHandler.get_header: header_name={self._header_name}, "
            f"api_key={_mask_value(key)}"
        )
        return {self._header_name: key}


def create_auth_handler(config: AuthConfig) -> AuthHandler:
    """Create auth handler from config."""
    # Use api_key property which computes the value for basic/complex types
    computed_key = config.api_key
    raw_key = config.raw_api_key.get_secret_value() if config.raw_api_key else None
    
    logger.debug(
        f"{LOG_PREFIX} create_auth_handler: type={config.type}, "
        f"raw_api_key={_mask_value(raw_key)}, "
        f"email={_mask_value(config.email)}, username={_mask_value(config.username)}"
    )

    t = config.type

    # Basic Auth Family - Use CustomAuthHandler with pre-computed header
    if t in ("basic", "basic_email_token", "basic_token", "basic_email"):
         logger.debug(f"{LOG_PREFIX} create_auth_handler: Basic type detected, using computed key")
         return CustomAuthHandler(
             header_name="Authorization",
             api_key="Basic " + computed_key, # Prepend Basic if not handled by config? 
             # Wait, config.api_key returns JUST the base64 part for flexibility or the whole thing?
             # Let's check config.py: return b64(...) -> It returns just the base64 string.
             # So we must prepend "Basic " here.
             get_api_key_for_request=config.get_api_key_for_request
         )

    # Complex Bearer Types - Use CustomAuthHandler with pre-computed header
    if t in ("bearer_username_token", "bearer_username_password", 
             "bearer_email_token", "bearer_email_password"):
        logger.debug(f"{LOG_PREFIX} create_auth_handler: Complex Bearer type, using computed key")
        return CustomAuthHandler(
             header_name="Authorization",
             api_key="Bearer " + computed_key,
             get_api_key_for_request=config.get_api_key_for_request
        )

    # Simple Bearer Types
    if t in ("bearer", "bearer_oauth", "bearer_jwt"):
        logger.debug(f"{LOG_PREFIX} create_auth_handler: Bearer type, using raw_api_key")
        # For simple bearer, config.api_key == raw_api_key
        return BearerAuthHandler(raw_key, config.get_api_key_for_request)

    # X-API-Key
    if t == "x-api-key":
        logger.debug(f"{LOG_PREFIX} create_auth_handler: x-api-key type")
        return XApiKeyAuthHandler(raw_key, config.get_api_key_for_request)

    # Custom
    if t in ("custom", "custom_header"):
        logger.debug(f"{LOG_PREFIX} create_auth_handler: Custom type")
        return CustomAuthHandler(
            config.header_name or "Authorization",
            raw_key,
            config.get_api_key_for_request,
        )
        
    # HMAC
    if t == "hmac":
        raise NotImplementedError("HMAC NOT IMPLEMENTED")

    logger.warning(
        f"{LOG_PREFIX} create_auth_handler: Unknown type '{config.type}', defaulting to bearer"
    )
    return BearerAuthHandler(raw_key, config.get_api_key_for_request)
