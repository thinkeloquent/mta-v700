from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from .auth_type import AuthType
from .token_resolver import TokenResolverType

@dataclass
class AuthResolutionMeta:
    """Metadata about how authentication configuration was resolved."""
    resolved_from: Dict[str, str] = field(default_factory=dict)
    token_resolver: TokenResolverType = TokenResolverType.STATIC
    is_placeholder: bool = False

@dataclass
class AuthConfig:
    """Structure containing resolved authentication credentials."""
    type: AuthType
    provider_name: str
    resolution: AuthResolutionMeta
    
    # Credentials
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None
    header_name: Optional[str] = None
    header_value: Optional[str] = None
    
    # EdgeGrid Specifics
    client_token: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    base_url: Optional[str] = None
    headers_to_sign: Optional[list] = None
