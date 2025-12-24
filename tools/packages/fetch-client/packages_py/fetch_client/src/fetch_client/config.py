"""
Configuration models and validation for fetch-client.
"""
import base64
from typing import Any, Callable, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from dataclasses import dataclass

from .types import AuthType, RequestContext, Serializer

# Constants
DEFAULT_TIMEOUT_CONNECT = 5.0
DEFAULT_TIMEOUT_READ = 30.0
DEFAULT_TIMEOUT_WRITE = 10.0
DEFAULT_CONTENT_TYPE = "application/json"

class TimeoutConfig(BaseModel):
    """Timeout configuration."""
    connect: float = DEFAULT_TIMEOUT_CONNECT
    read: float = DEFAULT_TIMEOUT_READ
    write: float = DEFAULT_TIMEOUT_WRITE
    pool: Optional[float] = None

class AuthConfig(BaseModel):
    """Authentication configuration."""
    type: AuthType
    raw_api_key: Optional[SecretStr] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    email: Optional[str] = None
    header_name: Optional[str] = None
    
    # Callback for dynamic key resolution
    get_api_key_for_request: Optional[Callable[[RequestContext], Optional[str]]] = None

    @property
    def api_key(self) -> str:
        """
        Get the computed API key ready for the header.
        - For basic/complex bearer: Returns the base64 encoded string
        - For simple bearer/x-api-key: Returns the raw key
        """
        return self._format_auth_header_value()

    def _format_auth_header_value(self) -> str:
        """Format the auth header value based on type."""
        t = self.type
        
        # Helper for base64 encoding
        def b64(s: str) -> str:
            return base64.b64encode(s.encode()).decode()

        # Basic Auth Family
        if t == "basic":
            if self.username and self.password:
                return b64(f"{self.username}:{self.password.get_secret_value()}")
            # Fallback/Error case logic handled in validation
            return "" # Should be valid if validation passes
            
        if t == "basic_email_token":
            if self.email and self.raw_api_key:
                return b64(f"{self.email}:{self.raw_api_key.get_secret_value()}")
                
        if t == "basic_token":
            if self.username and self.raw_api_key:
                return b64(f"{self.username}:{self.raw_api_key.get_secret_value()}")
        
        if t == "basic_email":
            if self.email and self.password:
                return b64(f"{self.email}:{self.password.get_secret_value()}")

        # Bearer Auth Family (Complex)
        if t == "bearer_username_token":
            if self.username and self.raw_api_key:
                return b64(f"{self.username}:{self.raw_api_key.get_secret_value()}")
                
        if t == "bearer_username_password":
            if self.username and self.password:
                return b64(f"{self.username}:{self.password.get_secret_value()}")
                
        if t == "bearer_email_token":
             if self.email and self.raw_api_key:
                return b64(f"{self.email}:{self.raw_api_key.get_secret_value()}")

        if t == "bearer_email_password":
             if self.email and self.password:
                return b64(f"{self.email}:{self.password.get_secret_value()}")

        # Simple types (Raw value)
        if self.raw_api_key:
            return self.raw_api_key.get_secret_value()
            
        return ""

    def get_auth_header_name(self) -> str:
        """Get the expected header name."""
        if self.type in ("x-api-key",):
            return "x-api-key"
        if self.type in ("custom", "custom_header"):
            return self.header_name or "Authorization"
        return "Authorization"

    @model_validator(mode='after')
    def validate_auth_config(self) -> 'AuthConfig':
        """Validate that required fields are present for the selected auth type."""
        t = self.type
        
        # Helpers
        has_user = bool(self.username)
        has_pass = bool(self.password)
        has_email = bool(self.email)
        has_key = bool(self.raw_api_key)

        if t == "basic" and not (has_user and has_pass):
            raise ValueError("Basic auth requires 'username' and 'password'")
            
        if t == "basic_email_token" and not (has_email and has_key):
             raise ValueError("basic_email_token requires 'email' and 'raw_api_key'")
             
        if t == "basic_token" and not (has_user and has_key):
             raise ValueError("basic_token requires 'username' and 'raw_api_key'")
             
        if t == "basic_email" and not (has_email and has_pass):
             raise ValueError("basic_email requires 'email' and 'password'")

        if t in ("bearer", "bearer_oauth", "bearer_jwt", "x-api-key") and not has_key:
            raise ValueError(f"{t} requires 'raw_api_key'")

        if t == "bearer_username_token" and not (has_user and has_key):
             raise ValueError("bearer_username_token requires 'username' and 'raw_api_key'")
             
        if t == "bearer_username_password" and not (has_user and has_pass):
             raise ValueError("bearer_username_password requires 'username' and 'password'")
             
        if t == "bearer_email_token" and not (has_email and has_key):
             raise ValueError("bearer_email_token requires 'email' and 'raw_api_key'")
             
        if t == "bearer_email_password" and not (has_email and has_pass):
             raise ValueError("bearer_email_password requires 'email' and 'password'")
             
        if t in ("custom", "custom_header") and not (self.header_name and has_key):
            raise ValueError(f"{t} requires 'header_name' and 'raw_api_key'")
            
        if t == "hmac":
            raise NotImplementedError("HMAC auth not yet implemented")

        return self

class DefaultSerializer:
    """Default JSON serializer."""
    def serialize(self, data: Any) -> str:
        import json
        return json.dumps(data)
        
    def deserialize(self, data: str) -> Any:
        import json
        return json.loads(data)

class ClientConfig(BaseModel):
    """Client configuration."""
    model_config = {"arbitrary_types_allowed": True}

    base_url: str
    auth: Optional[AuthConfig] = None
    timeout: Optional[Union[float, TimeoutConfig]] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    content_type: str = DEFAULT_CONTENT_TYPE
    
    # Optional pre-configured client (httpx)
    httpx_client: Any = None 
    
    # Custom serializer
    serializer: Optional[Serializer] = None

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")

def normalize_timeout(timeout: Optional[Union[float, TimeoutConfig]]) -> TimeoutConfig:
    """Normalize timeout to TimeoutConfig object."""
    if timeout is None:
        return TimeoutConfig()
    if isinstance(timeout, (int, float)):
        return TimeoutConfig(connect=float(timeout), read=float(timeout), write=float(timeout))
    return timeout

@dataclass
class ResolvedConfig:
    """Fully resolved configuration ready for usage."""
    base_url: str
    auth: Optional[AuthConfig]
    timeout: TimeoutConfig
    headers: Dict[str, str]
    content_type: str
    serializer: Serializer

def resolve_config(config: ClientConfig) -> ResolvedConfig:
    """Apply defaults and return resolved config."""
    return ResolvedConfig(
        base_url=config.base_url,
        auth=config.auth,
        timeout=normalize_timeout(config.timeout),
        headers=config.headers,
        content_type=config.content_type,
        serializer=config.serializer or DefaultSerializer()
    )
