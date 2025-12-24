"""
Fetch Client - Polyglot HTTP Client
"""

__version__ = "0.1.0"

from .config import ClientConfig, AuthConfig
from .types import AuthType
from .client import FetchClient
from .core.request import RequestBuilder
from .auth.auth_handler import AuthHandler, create_auth_handler
from .health import FetchStatus, FetchStatusResult, FetchStatusChecker

__all__ = [
    "ClientConfig", "AuthConfig", "AuthType",
    "FetchClient",
    "RequestBuilder",
    "AuthHandler", "create_auth_handler",
    "FetchStatus", "FetchStatusResult", "FetchStatusChecker"
]
