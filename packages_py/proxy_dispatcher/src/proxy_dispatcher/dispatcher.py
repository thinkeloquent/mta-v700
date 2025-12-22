"""
Convenience functions for proxy dispatcher.
"""
from typing import Optional, Dict, Any, Union
import httpx
from .factory import ProxyDispatcherFactory
from .models import FactoryConfig, DispatcherResult

# Global default factory
_default_factory = ProxyDispatcherFactory()

def get_proxy_dispatcher(
    environment: Optional[str] = None,
    disable_tls: Optional[bool] = None,
    timeout: float = 30.0,
    async_client: bool = True
) -> DispatcherResult:
    """Get a configured HTTP client using the default factory."""
    return _default_factory.get_proxy_dispatcher(
        environment=environment,
        disable_tls=disable_tls,
        timeout=timeout,
        async_client=async_client
    )

def get_async_client(
    disable_tls: Optional[bool] = None,
    timeout: float = 30.0
) -> httpx.AsyncClient:
    """Get a configured async httpx client."""
    result = get_proxy_dispatcher(disable_tls=disable_tls, timeout=timeout, async_client=True)
    return result.client

def get_sync_client(
    disable_tls: Optional[bool] = None,
    timeout: float = 30.0
) -> httpx.Client:
    """Get a configured sync httpx client."""
    result = get_proxy_dispatcher(disable_tls=disable_tls, timeout=timeout, async_client=False)
    return result.client

def get_request_kwargs(
    timeout: float = 30.0,
    ca_bundle: Optional[str] = None
) -> Dict[str, Any]:
    """Get kwargs for direct request calls."""
    return _default_factory.get_request_kwargs(timeout=timeout, ca_bundle=ca_bundle)

def create_proxy_dispatcher_factory(
    config: Optional[FactoryConfig] = None,
    adapter: str = "httpx"
) -> ProxyDispatcherFactory:
    """Create a new ProxyDispatcherFactory instance."""
    return ProxyDispatcherFactory(config=config, adapter=adapter)
