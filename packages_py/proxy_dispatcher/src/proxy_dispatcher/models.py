"""
Data models for proxy dispatcher.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union
from proxy_config import NetworkConfig, AgentProxyConfig

@dataclass
class ProxyConfig:
    """Resolved proxy configuration for HTTP clients."""
    proxy_url: Optional[str] = None
    verify_ssl: bool = False
    timeout: float = 30.0
    trust_env: bool = False
    cert: Optional[Union[str, tuple]] = None
    ca_bundle: Optional[str] = None

@dataclass
class FactoryConfig:
    """Configuration for ProxyDispatcherFactory."""
    proxy_urls: Optional[Dict[str, Optional[str]]] = None
    proxy_url: Optional[Union[str, bool]] = None
    agent_proxy: Optional[AgentProxyConfig] = None
    default_environment: Optional[str] = None
    cert: Optional[Union[str, tuple]] = None
    ca_bundle: Optional[str] = None
    cert_verify: Optional[bool] = None

@dataclass
class DispatcherResult:
    """Result wrapper with client, config, and kwargs."""
    client: Any  # Union[httpx.Client, httpx.AsyncClient]
    config: ProxyConfig
    proxy_dict: Dict[str, Any]
