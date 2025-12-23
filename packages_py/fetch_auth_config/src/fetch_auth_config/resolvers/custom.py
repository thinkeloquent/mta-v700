from ..types.auth_config import AuthConfig, AuthResolutionMeta
from ..types.auth_type import AuthType
from ..types.token_resolver import TokenResolverType
from ..errors import MissingCredentialError
from ..resolution.config_extractor import ProviderEnvMappings, AuthSettings
from ..resolution.env_resolver import resolve_env_var_chain

def resolve_custom_auth(
    provider_name: str,
    env_mappings: ProviderEnvMappings,
    auth_settings: AuthSettings
) -> AuthConfig:
    # Resolve value (token/value)
    token_res = resolve_env_var_chain(
        primary=env_mappings.api_key.primary,
        overwrite=env_mappings.api_key.overwrite,
        fallbacks=env_mappings.api_key.fallbacks
    )
    
    if not token_res.value:
        raise MissingCredentialError(provider_name, 'token', token_res.tried)
        
    resolved_from = {'token': token_res.source}
    
    # Resolve header name
    header_name = auth_settings.custom_header_name
    if auth_settings.auth_type == AuthType.X_API_KEY:
        header_name = "X-API-Key"
    
    if not header_name and auth_settings.auth_type != AuthType.TOP_LEVEL_CUSTOM: 
        # For 'custom_header' it is required. For strict custom maybe not?
        # Spec says: required: ['token', 'headerName']
        raise ValueError(f"Missing custom header name for provider '{provider_name}'")

    return AuthConfig(
        type=auth_settings.auth_type,
        provider_name=provider_name,
        token=token_res.value, # Acts as value
        header_name=header_name,
        resolution=AuthResolutionMeta(
            resolved_from=resolved_from,
            token_resolver=TokenResolverType.STATIC,
            is_placeholder=False
        )
    )
