"""
Models for Fetch Status Health Check.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

class FetchStatus(str, Enum):
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
    provider_name: str
    status: FetchStatus
    latency_ms: float
    timestamp: str
    request: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    config_used: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
