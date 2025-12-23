from typing import Optional
from .types.auth_config import AuthConfig
from .types.auth_type import AuthType
from .types.token_resolver import TokenResolverType
from .resolution.config_extractor import extract_env_mappings, extract_auth_settings
from .resolvers.bearer import resolve_bearer_auth
from .resolvers.basic import resolve_basic_auth
from .resolvers.custom import resolve_custom_auth
from .errors import InvalidAuthTypeError

def fetch_auth_config(
    provider_name: str,
    provider_config: dict # Dictionary from app-yaml-config
) -> AuthConfig:
    """
    Main entry point to resolve authentication configuration for a provider.
    
    Args:
        provider_name: The name of the provider (logging/error purposes).
        provider_config: The raw dictionary configuration from YAML.
    """
    
    # 1. Extract settings
    auth_settings = extract_auth_settings(provider_config)
    env_mappings = extract_env_mappings(provider_config)
    
    # 2. Route to resolver
    t = auth_settings.auth_type
    
    if t in [AuthType.BEARER, AuthType.BEARER_OAUTH, AuthType.BEARER_JWT]:
        return resolve_bearer_auth(provider_name, env_mappings, t)
        
    if t in [AuthType.BASIC, AuthType.BASIC_EMAIL_TOKEN, AuthType.BASIC_TOKEN, AuthType.BASIC_EMAIL]:
        return resolve_basic_auth(provider_name, env_mappings, t)
        
    if t in [AuthType.X_API_KEY, AuthType.CUSTOM, AuthType.CUSTOM_HEADER]:
        return resolve_custom_auth(provider_name, env_mappings, auth_settings)
        
    if t == AuthType.NONE:
        from .types.auth_config import AuthResolutionMeta # circular import avoidance if structured poorly, but here OK
        return AuthConfig(
            type=AuthType.NONE,
            provider_name=provider_name,
            resolution=AuthResolutionMeta(resolved_from={})
        )

    raise InvalidAuthTypeError(provider_name, str(t))
