"""
Core type definitions for fetch-client.
"""
from typing import Any, Dict, Literal, Optional, Protocol, TypedDict, Union, runtime_checkable
from dataclasses import dataclass, field

# HTTP Methods
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

# Authentication Types (15 types)
AuthType = Literal[
    "basic",
    "basic_email_token",
    "basic_token",
    "basic_email",
    "bearer",
    "bearer_oauth",
    "bearer_jwt",
    "bearer_username_token",
    "bearer_username_password",
    "bearer_email_token",
    "bearer_email_password",
    "x-api-key",
    "custom",
    "custom_header",
    "hmac",
]

@dataclass
class FetchResponse:
    """Standardized response object."""
    status: int
    status_text: str
    headers: Dict[str, str]
    url: str
    data: Any = None  # Parsed JSON or Text
    ok: bool = False

    @property
    def is_success(self) -> bool:
        """Check if status code is 2xx."""
        return 200 <= self.status <= 299

class RequestOptions(TypedDict, total=False):
    """Options for making a request."""
    method: HttpMethod
    url: str  # Full URL or path relative to base_url
    headers: Dict[str, str]
    params: Dict[str, Any]  # Query parameters
    json: Any
    data: Any  # Raw body (bytes/str/generator)
    timeout: Union[float, None]

class StreamOptions(RequestOptions):
    """Options for streaming requests."""
    on_event: Any  # Callable[[Any], None]

@dataclass
class SSEEvent:
    """Server-Sent Event data."""
    data: str
    id: Optional[str] = None
    event: Optional[str] = None
    retry: Optional[int] = None

@dataclass
class DiagnosticsEvent:
    """Event for diagnostics/observability."""
    name: str  # 'request:start', 'request:end', 'request:error'
    timestamp: float
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    status: Optional[int] = None
    duration: Optional[float] = None
    error: Optional[Exception] = None

class RequestContext(TypedDict):
    """Context passed to auth callbacks."""
    method: str
    url: str
    headers: Dict[str, str]
    body: Any

@runtime_checkable
class Serializer(Protocol):
    """Protocol for serialization."""
    def serialize(self, data: Any) -> str: ...
    def deserialize(self, data: str) -> Any: ...
