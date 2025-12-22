"""
Proxy URL resolution logic.
"""
import os
import logging
from typing import Optional, Union
from .types import NetworkConfig

logger = logging.getLogger(__name__)

def resolve_proxy_url(
    network_config: Optional[NetworkConfig] = None,
    proxy_url_override: Optional[Union[str, bool]] = None
) -> Optional[str]:
    """Resolve the proxy URL based on configuration and environment.
    
    Precedence:
    1. proxy_url_override (if False, explicitly disable proxy)
    2. proxy_url_override (if string, return it)
    3. network_config.agent_proxy.https_proxy
    4. network_config.agent_proxy.http_proxy
    5. network_config.proxy_urls[default_environment]
    6. PROXY_URL env var
    7. HTTPS_PROXY env var
    8. HTTP_PROXY env var
    """
    logger.debug(f"Resolving proxy URL. Config: {bool(network_config)}, Override: {proxy_url_override}")

    # 1. Explicit disable
    if proxy_url_override is False:
        logger.debug("Proxy explicitly disabled via override=False")
        return None

    # 2. Explicit override
    if isinstance(proxy_url_override, str) and proxy_url_override:
        logger.debug("Using explicit proxy URL override")
        return proxy_url_override

    # Check network config sources
    if network_config:
        # 3 & 4. Agent proxy config
        if network_config.agent_proxy:
            if network_config.agent_proxy.https_proxy:
                logger.debug("Using agent_proxy.https_proxy")
                return network_config.agent_proxy.https_proxy
            if network_config.agent_proxy.http_proxy:
                logger.debug("Using agent_proxy.http_proxy")
                return network_config.agent_proxy.http_proxy

        # 5. Environment-specific proxy URL
        if network_config.default_environment:
            env_proxy = network_config.proxy_urls.get(network_config.default_environment)
            if env_proxy:
                logger.debug(f"Using proxy URL for environment '{network_config.default_environment}'")
                return env_proxy

    # Env var fallback
    # 6. PROXY_URL
    proxy_url_env = os.getenv("PROXY_URL")
    if proxy_url_env:
        logger.debug("Using PROXY_URL env var")
        return proxy_url_env

    # 7. HTTPS_PROXY
    https_proxy_env = os.getenv("HTTPS_PROXY")
    if https_proxy_env:
        logger.debug("Using HTTPS_PROXY env var")
        return https_proxy_env

    # 8. HTTP_PROXY
    http_proxy_env = os.getenv("HTTP_PROXY")
    if http_proxy_env:
        logger.debug("Using HTTP_PROXY env var")
        return http_proxy_env

    logger.debug("No proxy URL found")
    return None
