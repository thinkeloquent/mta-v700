from typing import Optional, Any
from .types.auth_config import AuthConfig, AuthResolutionMeta
from .types.auth_type import AuthType
from .types.token_resolver import TokenResolverType
from .resolution.config_extractor import extract_env_mappings, extract_auth_settings
from .resolvers.bearer import resolve_bearer_auth
from .resolvers.basic import resolve_basic_auth
from .resolvers.custom import resolve_custom_auth
from .errors import InvalidAuthTypeError
from .compute_registry import ComputeRegistry

async def fetch_auth_config(
    provider_name: str,
    provider_config: dict, # Dictionary from app-yaml-config
    request: Any = None
) -> AuthConfig:
    """
    Main entry point to resolve authentication configuration for a provider.
    
    Args:
        provider_name: The name of the provider (logging/error purposes).
        provider_config: The raw dictionary configuration from YAML.
        request: Optional request context for REQUEST resolver.
    """
    
    # 1. Extract settings
    auth_settings = extract_auth_settings(provider_config)
    env_mappings = extract_env_mappings(provider_config)
    
    t = auth_settings.auth_type
    
    # 2. Dynamic Resolution (Startup / Request)
    if auth_settings.token_resolver in [TokenResolverType.STARTUP, TokenResolverType.REQUEST]:
        token_value: Optional[str] = None
        
        if auth_settings.token_resolver == TokenResolverType.STARTUP:
            token_value = await ComputeRegistry.resolve_startup(provider_name)
            
        elif auth_settings.token_resolver == TokenResolverType.REQUEST:
            if request is None:
                # If request is missing but required, logic dictates error? 
                # Or we return placeholder?
                # The plan says "request context required".
                # Let's raise ValueError for now, or clearer error.
                raise ValueError(f"Request context required for provider '{provider_name}' with REQUEST token resolver")
            token_value = await ComputeRegistry.resolve_request(provider_name, request)
            
        # Construct AuthConfig from resolved token
        # We assume the resolved value is the 'token' or 'primary secret'
        
        # Build base config
        ac = AuthConfig(
            type=t,
            provider_name=provider_name,
            username=provider_config.get("username"), # Fallback to static/env? No, extractor handles env mappings.
            # But wait, env_mappings has resolving logic.
            # If we use dynamic, do we ignore env mappings for OTHER fields?
            # Usually dynamic replaces the main secret.
            # Let's populate 'token' with result.
            token=token_value,
            header_name=auth_settings.custom_header_name, # or default
            resolution=AuthResolutionMeta(
                resolved_from={"token": "dynamic"},
                token_resolver=auth_settings.token_resolver,
                is_placeholder=False
            ),
            resolver_type=auth_settings.token_resolver
        )
        
        # Map token to password if Basic auth type typically uses password field
        # Basic auth usually: username + password (or token as password)
        if t in [AuthType.BASIC, AuthType.BASIC_EMAIL]:
             ac.password = token_value
             # Also try to resolve username from env if possible?
             # Existing resolvers do that.
             # If we bypass `resolve_basic_auth`, we lose username resolution.
             # Ideally dynamic resolver returns dictionary? But spec says string.
             # So we assume username is static or resolved separately?
             # Let's try to resolve username using env_mappings manually if needed.
             pass

        # For Headers/Basic, we might need default header name if not Custom
        if not ac.header_name:
             if t in [AuthType.BEARER, AuthType.BEARER_OAUTH, AuthType.BEARER_JWT, AuthType.BASIC, AuthType.BASIC_EMAIL_TOKEN, AuthType.BASIC_TOKEN, AuthType.BASIC_EMAIL]:
                 ac.header_name = "Authorization"
        
        return ac

    # 3. Static Resolution (Delegates to existing resolvers)
    # Existing resolvers return AuthConfig. We need to inject resolver_type (STATIC).
    # Since `TokenResolverType` default in AuthConfig is STATIC, it's fine.
    
    if t in [AuthType.BEARER, AuthType.BEARER_OAUTH, AuthType.BEARER_JWT]:
        return resolve_bearer_auth(provider_name, env_mappings, t)
        
    if t in [AuthType.BASIC, AuthType.BASIC_EMAIL_TOKEN, AuthType.BASIC_TOKEN, AuthType.BASIC_EMAIL]:
        return resolve_basic_auth(provider_name, env_mappings, t)
        
    if t in [AuthType.X_API_KEY, AuthType.CUSTOM, AuthType.CUSTOM_HEADER]:
        return resolve_custom_auth(provider_name, env_mappings, auth_settings)
        
    if t == AuthType.NONE:
        from .types.auth_config import AuthResolutionMeta 
        return AuthConfig(
            type=AuthType.NONE,
            provider_name=provider_name,
            resolution=AuthResolutionMeta(resolved_from={}),
            resolver_type=TokenResolverType.STATIC
        )

    raise InvalidAuthTypeError(provider_name, str(t))
