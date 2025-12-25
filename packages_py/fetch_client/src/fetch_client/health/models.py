"""
Models for Fetch Status Health Check.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class FetchStatus(str, Enum):
    """Status codes for fetch health checks."""
    CONNECTED = "connected"
    UNAUTHORIZED = "unauthorized"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    CONFIG_ERROR = "config_error"
    ERROR = "error"


@dataclass
class FetchStatusResult:
    """Result of a fetch status health check."""
    provider_name: str
    status: FetchStatus
    latency_ms: float
    timestamp: str
    request: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    config_used: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "provider_name": self.provider_name,
            "status": self.status.value if isinstance(self.status, FetchStatus) else self.status,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }
        if self.request is not None:
            result["request"] = self.request
        if self.response is not None:
            result["response"] = self.response
        if self.config_used is not None:
            result["config_used"] = self.config_used
        if self.error is not None:
            result["error"] = self.error
        return result
