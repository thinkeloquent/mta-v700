"""
Adapter for httpx library.
"""
import logging
import httpx
from typing import Any, Dict
from .base import BaseAdapter
from ..models import DispatcherResult, ProxyConfig

logger = logging.getLogger(__name__)

class HttpxAdapter(BaseAdapter):
    """Adapter for httpx library."""

    @property
    def name(self) -> str:
        return "httpx"

    def supports_sync(self) -> bool:
        return True

    def supports_async(self) -> bool:
        return True

    def get_proxy_dict(self, config: ProxyConfig) -> Dict[str, Any]:
        """Build kwargs for httpx client."""
        kwargs: Dict[str, Any] = {
            "timeout": config.timeout,
            "verify": config.verify_ssl,
        }
        
        if config.proxy_url:
            kwargs["proxy"] = config.proxy_url
            
        if config.cert:
            kwargs["cert"] = config.cert
            
        # httpx specific: 'trust_env' defaults to True in httpx, but we control it
        # Actually httpx uses 'trust_env', defaulting to True. 
        # If we set it to False, it won't read env vars.
        kwargs["trust_env"] = config.trust_env

        return kwargs

    def create_sync_client(self, config: ProxyConfig) -> DispatcherResult:
        """Create httpx.Client."""
        kwargs = self.get_proxy_dict(config)
        logger.debug(f"Creating httpx.Client with config: {kwargs}")
        
        client = httpx.Client(**kwargs)
        
        return DispatcherResult(
            client=client,
            config=config,
            proxy_dict=kwargs
        )

    def create_async_client(self, config: ProxyConfig) -> DispatcherResult:
        """Create httpx.AsyncClient."""
        kwargs = self.get_proxy_dict(config)
        logger.debug(f"Creating httpx.AsyncClient with config: {kwargs}")
        
        client = httpx.AsyncClient(**kwargs)
        
        return DispatcherResult(
            client=client,
            config=config,
            proxy_dict=kwargs
        )
