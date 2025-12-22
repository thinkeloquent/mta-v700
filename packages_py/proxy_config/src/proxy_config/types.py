"""
Data models for proxy configuration.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field

class AgentProxyConfig(BaseModel):
    """Configuration for HTTP_PROXY/HTTPS_PROXY overrides.
    
    These settings are typically cleared from the environment by the
    agent_proxy logic to prevent double-proxying, but can be explicitly
    passed here to be used by the resolver.
    """
    http_proxy: Optional[str] = Field(default=None, description="HTTP proxy URL")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS proxy URL")

class NetworkConfig(BaseModel):
    """Network configuration settings from app.yaml.
    
    Contains environment-specific proxy URLs and global SSL settings.
    """
    default_environment: Optional[str] = Field(default="dev", description="Default environment to use if parsing fails")
    proxy_urls: Dict[str, Optional[str]] = Field(default_factory=dict, description="Map of environment names to proxy URLs")
    ca_bundle: Optional[str] = Field(default=None, description="Path to CA bundle file")
    cert: Optional[str] = Field(default=None, description="Path to client certificate")
    cert_verify: bool = Field(default=False, description="Whether to verify SSL certificates")
    agent_proxy: Optional[AgentProxyConfig] = Field(default=None, description="Agent proxy configuration")
