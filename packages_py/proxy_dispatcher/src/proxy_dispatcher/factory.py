"""
Factory for creating proxy-configured HTTP clients.
"""
import logging
from typing import Optional, Dict, Any, Union
from proxy_config import NetworkConfig, resolve_proxy_url
from .models import FactoryConfig, ProxyConfig, DispatcherResult
from .config import get_app_env, is_dev, is_ssl_verify_disabled_by_env
from .adapters import get_adapter, BaseAdapter

logger = logging.getLogger(__name__)

class ProxyDispatcherFactory:
    """Factory for creating proxy-configured HTTP clients."""
    
    def __init__(
        self, 
        config: Optional[FactoryConfig] = None,
        adapter: str = "httpx"
    ):
        self.config = config or FactoryConfig()
        self.adapter: BaseAdapter = get_adapter(adapter)
        
        # Load network config from app.yaml if available (would be passed in config usually)
        # For this implementation, we assume config is passed explicitly or resolves from env
        # In full integration, we'd load NetworkConfig here if not provided.
        
        logger.debug(f"ProxyDispatcherFactory initialized with adapter '{adapter}'")

    def get_proxy_dispatcher(
        self,
        environment: Optional[str] = None,
        disable_tls: Optional[bool] = None,
        timeout: float = 30.0,
        async_client: bool = True
    ) -> DispatcherResult:
        """Get a configured HTTP client."""
        
        # 1. Determine environment
        target_env = environment or self.config.default_environment or get_app_env()
        logger.debug(f"Target environment: {target_env}")

        # 2. Resolve Proxy URL
        # Build NetworkConfig-like structure from FactoryConfig for resolver
        # This maps FactoryConfig fields to what resolver expects
        network_config = NetworkConfig(
            default_environment=self.config.default_environment,
            proxy_urls=self.config.proxy_urls or {},
            agent_proxy=self.config.agent_proxy,
            cert=self.config.cert,
            ca_bundle=self.config.ca_bundle
        )
        
        proxy_url = resolve_proxy_url(
            network_config=network_config,
            proxy_url_override=self.config.proxy_url
        )

        # 3. Determine SSL Settings
        # Precedence: disable_tls param > config.cert_verify > environment default
        verify_ssl = True
        
        if disable_tls is True:
            verify_ssl = False
        elif self.config.cert_verify is not None:
            verify_ssl = self.config.cert_verify
        elif is_ssl_verify_disabled_by_env():
             verify_ssl = False
        # If we are in dev and trust_env is defaulting to false, we might want to disable verify
        # But generally verify should be true unless explicitly disabled.
        
        # 4. Build ProxyConfig
        proxy_config = ProxyConfig(
            proxy_url=proxy_url,
            verify_ssl=verify_ssl,
            timeout=timeout,
            trust_env=False, # We explicitly configure everything
            cert=self.config.cert,
            ca_bundle=self.config.ca_bundle
        )
        
        # 5. Create Client via Adapter
        if async_client:
            if not self.adapter.supports_async():
                raise NotImplementedError(f"Adapter '{self.adapter.name}' does not support async")
            return self.adapter.create_async_client(proxy_config)
        else:
            if not self.adapter.supports_sync():
                raise NotImplementedError(f"Adapter '{self.adapter.name}' does not support sync")
            return self.adapter.create_sync_client(proxy_config)

    def get_dispatcher_for_environment(
        self,
        environment: str,
        async_client: bool = True
    ) -> DispatcherResult:
        """Get dispatcher for a specific environment."""
        return self.get_proxy_dispatcher(environment=environment, async_client=async_client)

    def get_request_kwargs(
        self,
        timeout: float = 30.0,
        ca_bundle: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get kwargs for direct request calls (e.g. httpx.get)."""
        # Create a temp config to resolve settings
        result = self.get_proxy_dispatcher(timeout=timeout, async_client=True) # async/sync doesn't matter for kwargs
        return result.proxy_dict
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        result = self.get_proxy_dispatcher()
        return result.proxy_dict
