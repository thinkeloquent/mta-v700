
import os
from dataclasses import dataclass
from typing import Any, List, Literal, Optional, Union

ProxySource = Literal['disabled', 'env_overwrite', 'provider_direct', 'env_proxy', 'global_fallback']

@dataclass
class ProxyResolutionResult:
    proxy_url: Optional[str]
    source: ProxySource
    env_var_used: Optional[str]
    original_value: Any
    global_proxy: Optional[str]
    app_env: str


def resolve_provider_proxy(
    provider_name: str,
    provider_config: dict,
    global_config: dict,
    app_env: str
) -> ProxyResolutionResult:
    """Resolve the effective proxy URL for a provider."""

    original_value = provider_config.get('proxy_url')
    global_proxy = (global_config.get('network') or {}).get('proxy_urls', {}).get(app_env)

    result = ProxyResolutionResult(
        proxy_url=None,
        source='disabled',
        env_var_used=None,
        original_value=original_value,
        global_proxy=global_proxy,
        app_env=app_env,
    )

    # 1. Check overwrite_from_env.proxy_url first
    overwrite_from_env = provider_config.get('overwrite_from_env', {})
    proxy_env_override = overwrite_from_env.get('proxy_url')

    if proxy_env_override:
        env_var_names = proxy_env_override if isinstance(proxy_env_override, list) else [proxy_env_override]

        for env_var_name in env_var_names:
            env_value = os.environ.get(env_var_name)
            if env_value is not None and env_value != '':
                result.proxy_url = env_value
                result.source = 'env_overwrite'
                result.env_var_used = env_var_name
                return result

    # 2. Resolve based on proxy_url value type
    if original_value is False:
        # Explicitly disabled
        result.proxy_url = None
        result.source = 'disabled'
        return result

    if original_value is None:
        # Inherit from global
        result.proxy_url = global_proxy
        result.source = 'global_fallback'
        return result

    if original_value is True:
        # Use standard env vars
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        env_proxy = https_proxy or http_proxy

        result.proxy_url = env_proxy
        result.source = 'env_proxy'
        result.env_var_used = 'HTTPS_PROXY' if https_proxy else ('HTTP_PROXY' if http_proxy else None)
        return result

    if isinstance(original_value, str):
        # Direct URL/IP value
        result.proxy_url = original_value
        result.source = 'provider_direct'
        return result

    # Fallback: treat as null (inherit global)
    result.proxy_url = global_proxy
    result.source = 'global_fallback'
    return result
