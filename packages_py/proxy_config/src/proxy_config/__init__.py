"""
Proxy configuration and resolution package.
"""
from .types import NetworkConfig, AgentProxyConfig
from .resolver import resolve_proxy_url

__all__ = [
    "NetworkConfig",
    "AgentProxyConfig",
    "resolve_proxy_url",
]
