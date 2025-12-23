
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal
from fetch_auth_config import fetch_auth_config, AuthConfig
from fetch_auth_encoding import encode_auth


@dataclass
class AuthResolutionResult:
    """Result of resolving authentication for a provider."""
    auth_config: AuthConfig
    headers: Dict[str, str]
    provider_name: str
    source: Literal['provider_config', 'env_overwrite', 'default']


@dataclass
class ResolveAuthOptions:
    """Options for auth resolution."""
    include_headers: bool = True


def resolve_provider_auth(
    provider_name: str,
    provider_config: Dict[str, Any],
    options: Optional[ResolveAuthOptions] = None
) -> AuthResolutionResult:
    """
    Resolve authentication configuration for a provider.
    Thin wrapper around fetch_auth_config that mirrors resolve_provider_proxy pattern.

    Args:
        provider_name: Name of the provider
        provider_config: Provider configuration dict
        options: Resolution options

    Returns:
        AuthResolutionResult with auth config, headers, and source info
    """
    opts = options or ResolveAuthOptions()

    # Use fetch_auth_config for credential resolution
    auth_config = fetch_auth_config(provider_name, provider_config)

    # Build headers if requested
    headers: Dict[str, str] = {}
    if opts.include_headers:
        creds = _build_credentials(auth_config)
        headers = encode_auth(auth_config.type.value if hasattr(auth_config.type, 'value') else str(auth_config.type), **creds)

    # Determine source based on resolution metadata
    source: Literal['provider_config', 'env_overwrite', 'default'] = 'provider_config'
    if auth_config.resolution and auth_config.resolution.resolved_from:
        if len(auth_config.resolution.resolved_from) > 0:
            source = 'env_overwrite'

    return AuthResolutionResult(
        auth_config=auth_config,
        headers=headers,
        provider_name=provider_name,
        source=source,
    )


def _build_credentials(auth_config: AuthConfig) -> Dict[str, Any]:
    """Build credentials dict from auth config."""
    creds: Dict[str, Any] = {}
    if auth_config.token:
        creds['token'] = auth_config.token
    if auth_config.username:
        creds['username'] = auth_config.username
    if auth_config.password:
        creds['password'] = auth_config.password
    if auth_config.email:
        creds['email'] = auth_config.email
    if auth_config.header_name:
        creds['header_key'] = auth_config.header_name
    if auth_config.header_value:
        creds['header_value'] = auth_config.header_value
    return creds
